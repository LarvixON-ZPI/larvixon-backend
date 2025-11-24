import os
import shutil
from django.urls import reverse
from django.utils import timezone
import datetime
from rest_framework import status
from rest_framework.test import APITestCase
from larvixon_site import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Substance, AnalysisResult, User, VideoAnalysis
from patients.models import Patient


class VideoAnalysisTest(APITestCase):
    def setUp(self):
        # User 1
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        # User 2
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpass123"
        )

        self.analysis_list_url = reverse("analysis:analysis-list")

        # Create Patients
        self.patient1 = Patient.objects.create(
            first_name="Jan",
            last_name="Kowalski",
            pesel="90010112345",
            birth_date=datetime.date(1990, 1, 1),
            sex=Patient.Sex.MALE,
        )
        self.patient2 = Patient.objects.create(
            first_name="Anna",
            last_name="Nowak",
            pesel="95050554321",
            birth_date=datetime.date(1995, 5, 5),
            sex=Patient.Sex.FEMALE,
        )

        # Create Substances
        self.substance1 = Substance.objects.create(name_en="Cocaine")
        self.substance2 = Substance.objects.create(name_en="Morphine")

        # Create Analyses for self.user
        video_content = b"fake video content"

        # Analysis 1: Completed, has Cocaine and some Morphine
        self.analysis1 = VideoAnalysis.objects.create(
            user=self.user,
            description="Cocaine Test",
            video=SimpleUploadedFile(
                "test_video1.mp4", video_content, content_type="video/mp4"
            ),
            status=VideoAnalysis.Status.COMPLETED,
            patient=self.patient1,
        )
        AnalysisResult.objects.create(
            analysis=self.analysis1, substance=self.substance1, confidence_score=0.95
        )
        AnalysisResult.objects.create(
            analysis=self.analysis1, substance=self.substance2, confidence_score=0.55
        )

        self.analysis1.created_at = timezone.now() - datetime.timedelta(days=2)
        self.analysis1.save()

        # Analysis 2: Completed, has Morphine and some Cocaine
        self.analysis2 = VideoAnalysis.objects.create(
            user=self.user,
            description="A Morphine Video",
            video=SimpleUploadedFile(
                "test_video2.mp4", video_content, content_type="video/mp4"
            ),
            status=VideoAnalysis.Status.COMPLETED,
            patient=self.patient2,
        )
        AnalysisResult.objects.create(
            analysis=self.analysis2, substance=self.substance2, confidence_score=0.80
        )
        AnalysisResult.objects.create(
            analysis=self.analysis2, substance=self.substance1, confidence_score=0.60
        )

        self.analysis2.created_at = timezone.now() - datetime.timedelta(days=1)
        self.analysis2.save()

        # Analysis 3: Pending, no results yet
        self.analysis3 = VideoAnalysis.objects.create(
            user=self.user,
            description="Surprise Analysis",
            video=SimpleUploadedFile(
                "test_video3.mp4", video_content, content_type="video/mp4"
            ),
            status=VideoAnalysis.Status.PENDING,
            created_at=timezone.now(),
            patient=None,
        )

        # Analysis 4: Belongs to other_user
        self.analysis4_other_user = VideoAnalysis.objects.create(
            user=self.other_user,
            description="Other User's Video",
            video=SimpleUploadedFile(
                "test_video4.mp4", video_content, content_type="video/mp4"
            ),
            status=VideoAnalysis.Status.FAILED,
        )

    def test_get_analysis_list(self):
        response = self.client.get(self.analysis_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)

    def test_create_analysis(self):
        fake_video = SimpleUploadedFile(
            "new_video.mp4", b"fake video content", content_type="video/mp4"
        )

        payload = {
            "description": "New Video Test",
            "video": fake_video,
        }

        self.assertEqual(VideoAnalysis.objects.count(), 4)

        response = self.client.post(self.analysis_list_url, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VideoAnalysis.objects.count(), 5)
        new_analysis = VideoAnalysis.objects.get(id=response.data["id"])
        video_name = os.path.basename(new_analysis.video.name)
        self.assertEqual(video_name, "new_video.mp4")

    def test_create_analysis_with_patient(self):
        fake_video = SimpleUploadedFile(
            "patient_video.mp4", b"content", content_type="video/mp4"
        )
        payload = {
            "description": "Analysis for Patient 1",
            "video": fake_video,
            "patient_id": self.patient1.id,
        }

        response = self.client.post(self.analysis_list_url, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_analysis = VideoAnalysis.objects.get(id=response.data["id"])
        self.assertEqual(new_analysis.patient, self.patient1)

    def test_get_analysis_detail_includes_patient(self):
        detail_url = reverse("analysis:analysis-detail", args=[self.analysis1.id])
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("patient_details", response.data)
        self.assertEqual(response.data["patient_details"]["last_name"], "Kowalski")
        self.assertEqual(response.data["patient_details"]["pesel"], "90010112345")

    def test_delete_analysis(self):
        analysis_to_delete = self.analysis1
        analysis_id = analysis_to_delete.id
        video_path = analysis_to_delete.video.path

        self.assertTrue(os.path.exists(video_path))

        detail_url = reverse("analysis:analysis-detail", args=[analysis_id])
        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(VideoAnalysis.DoesNotExist):
            VideoAnalysis.objects.get(id=analysis_id)

        self.assertFalse(os.path.exists(video_path))

    def test_get_analysis_detail(self):
        detail_url = reverse("analysis:analysis-detail", args=[self.analysis1.id])
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("video_name", response.data)
        self.assertTrue(response.data["video_name"].endswith("test_video1.mp4"))

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
        self.assertEqual(response.data["total_analyses"], 3)
        self.assertEqual(response.data["completed_analyses"], 2)
        self.assertEqual(response.data["pending_analyses"], 1)

    # --- Filter Tests ---

    def test_filter_by_status(self):
        response = self.client.get(self.analysis_list_url, {"status": "completed"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {self.analysis1.id, self.analysis2.id})

    def test_filter_by_description_icontains(self):
        response = self.client.get(
            self.analysis_list_url, {"description__icontains": "video"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.analysis2.id)

    def test_filter_by_related_substance_name(self):
        response = self.client.get(
            self.analysis_list_url, {"substance_name": "Cocaine"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {self.analysis1.id, self.analysis2.id})

    def test_filter_by_min_confidence(self):
        response = self.client.get(self.analysis_list_url, {"min_confidence": 0.90})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.analysis1.id)

    def test_filter_by_custom_substance_and_score(self):
        response = self.client.get(
            self.analysis_list_url, {"substance_and_score": "Cocaine,0.9"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.analysis1.id)

    def test_filter_by_custom_substance_and_score_no_match(self):
        response = self.client.get(
            self.analysis_list_url, {"substance_and_score": "Morphine,0.9"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    # --- Patient Filter Tests ---

    def test_filter_by_patient_last_name(self):
        response = self.client.get(
            self.analysis_list_url, {"patient_last_name": "Kowalski"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.analysis1.id)

    def test_filter_by_patient_first_name(self):
        response = self.client.get(
            self.analysis_list_url, {"patient_first_name": "Anna"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.analysis2.id)

    def test_filter_by_patient_pesel(self):
        response = self.client.get(
            self.analysis_list_url, {"patient_pesel": "95050554321"}
        )
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.analysis2.id)

    # --- Ordering Tests ---

    def test_ordering_by_description_ascending(self):
        response = self.client.get(self.analysis_list_url, {"ordering": "description"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        descriptions = [item["description"] for item in response.data["results"]]
        self.assertEqual(
            descriptions, ["A Morphine Video", "Cocaine Test", "Surprise Analysis"]
        )

    def test_ordering_by_description_descending(self):
        response = self.client.get(self.analysis_list_url, {"ordering": "-description"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        descriptions = [item["titdescriptionle"] for item in response.data["results"]]
        self.assertEqual(
            descriptions, ["Surprise Analysis", "Cocaine Test", "A Morphine Video"]
        )

    def test_default_ordering_created_at_descending(self):
        response = self.client.get(self.analysis_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [self.analysis3.id, self.analysis2.id, self.analysis1.id])

    # --- Permission Tests ---

    def test_get_list_unauthenticated(self):
        self.client.force_authenticate(user=None)  # Log out
        response = self.client.get(self.analysis_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_unauthenticated(self):
        self.client.force_authenticate(user=None)
        payload = {"description": "Should Fail"}
        response = self.client.post(self.analysis_list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_see_other_users_analysis_list(self):
        response = self.client.get(self.analysis_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)
        ids = {item["id"] for item in response.data["results"]}
        self.assertNotIn(self.analysis4_other_user.id, ids)

    def test_user_cannot_access_other_users_analysis_detail(self):
        detail_url = reverse(
            "analysis:analysis-detail", args=[self.analysis4_other_user.id]
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_update_other_users_analysis(self):
        detail_url = reverse(
            "analysis:analysis-detail", args=[self.analysis4_other_user.id]
        )
        response = self.client.patch(detail_url, {"description": "hacked"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_delete_other_users_analysis(self):
        detail_url = reverse(
            "analysis:analysis-detail", args=[self.analysis4_other_user.id]
        )
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Validation Tests ---

    def test_create_analysis_invalid_file_type(self):
        fake_text_file = SimpleUploadedFile(
            "not_a_video.txt", b"this is text", content_type="text/plain"
        )
        payload = {
            "description": "Text File Test",
            "video": fake_text_file,
        }
        response = self.client.post(self.analysis_list_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_analysis_invalid_data(self):
        detail_url = reverse("analysis:analysis-detail", args=[self.analysis1.id])
        payload = {
            "status": "an-invalid-choice",
        }
        response = self.client.patch(detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    # --- ID List Endpoint Tests ---

    def test_get_analysis_id_list(self):
        id_list_url = reverse("analysis:analysis-id-list")
        response = self.client.get(id_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.data["results"][0].keys(), {"id"})

    def test_get_analysis_id_list_filtered(self):
        id_list_url = reverse("analysis:analysis-id-list")
        response = self.client.get(id_list_url, {"status": "pending"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.analysis3.id)

    def tearDown(self):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
