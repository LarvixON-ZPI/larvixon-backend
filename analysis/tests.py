import os
import shutil
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from larvixon_site import settings
from .models import User
from analysis.models import VideoAnalysis
from django.core.files.uploadedfile import SimpleUploadedFile


class VideoAnalysisTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
        self.analysis_list_url = reverse("analysis:analysis-list")

        video_content = b"fake video content"
        video_file1 = SimpleUploadedFile(
            "test_video1.mp4", video_content, content_type="video/mp4"
        )
        video_file2 = SimpleUploadedFile(
            "test_video2.mp4", video_content, content_type="video/mp4"
        )

        # Create some test analyses
        self.analysis1 = VideoAnalysis.objects.create(
            user=self.user,
            video=video_file1,
            status="completed",
        )
        self.analysis2 = VideoAnalysis.objects.create(
            user=self.user,
            video=video_file2,
            status="pending",
        )

    def test_get_analysis_list(self):
        response = self.client.get(self.analysis_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_create_analysis(self):
        fake_video = SimpleUploadedFile(
            "new_video.mp4", b"fake video content", content_type="video/mp4"
        )

        payload = {
            "title": "New Video Test",
            "video": fake_video,
        }

        response = self.client.post(self.analysis_list_url, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VideoAnalysis.objects.count(), 3)
        video_name = os.path.basename(VideoAnalysis.objects.first().video.name)
        self.assertEqual(video_name, "new_video.mp4")

    def test_get_analysis_detail(self):
        detail_url = reverse("analysis:analysis-detail", args=[self.analysis1.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("video_url", response.data)
        self.assertTrue(response.data["video_url"].endswith("test_video1.mp4"))

    def test_update_analysis(self):
        detail_url = reverse("analysis:analysis-detail", args=[self.analysis1.id])
        payload = {
            "actual_substance": "cocaine",
            "user_feedback": "The analysis was accurate",
        }
        response = self.client.patch(detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.analysis1.refresh_from_db()
        self.assertEqual(self.analysis1.actual_substance, "cocaine")

    def test_user_stats(self):
        stats_url = reverse("accounts:user-stats")
        response = self.client.get(stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_analyses"], 2)
        self.assertEqual(response.data["completed_analyses"], 1)
        self.assertEqual(response.data["pending_analyses"], 1)

    def tearDown(self):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
