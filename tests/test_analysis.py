import sys
import os
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from accounts.models import User
from analysis.views.list_view import VideoAnalysisListView
from analysis.views.detail_view import VideoAnalysisDetailView
from analysis.views.retry_view import VideoAnalysisRetryView
from analysis.models import VideoAnalysis, Substance, AnalysisResult
from tests.common import TestFixtures, run_tests, cleanup_test_media

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "larvixon_site.settings")

import django

django.setup()

VIDEO_CONTENT = b"fake video content for testing"
VIDEO_FILENAME = "test_video.mp4"
VIDEO_CONTENT_TYPE = "video/mp4"
TEST_PASSWORD = "testpass123"


class TestVideoAnalysis(TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        cleanup_test_media()
        super().tearDownClass()

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        user_data: dict[str, str] = TestFixtures.get_test_user_data()
        self.user: User = User.objects.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=TEST_PASSWORD,
        )

    def tearDown(self) -> None:
        VideoAnalysis.objects.all().delete()
        User.objects.all().delete()

    def _create_video_file(self) -> SimpleUploadedFile:
        return SimpleUploadedFile(
            VIDEO_FILENAME, VIDEO_CONTENT, content_type=VIDEO_CONTENT_TYPE
        )

    def test_create_analysis(self) -> None:
        video_file: SimpleUploadedFile = self._create_video_file()

        request: Request = self.factory.post(
            "/api/analysis/",
            {"description": "test_video_unittest.mp4", "video": video_file},
            format="multipart",
        )
        force_authenticate(request, user=self.user)
        response: Response = VideoAnalysisListView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["description"], "test_video_unittest.mp4")
        self.assertEqual(response.data["status"], "pending")

    def test_get_analyses_list(self) -> None:
        video_file: SimpleUploadedFile = self._create_video_file()
        request: Request = self.factory.post(
            "/api/analysis/",
            {"description": "test_video.mp4", "video": video_file},
            format="multipart",
        )
        force_authenticate(request, user=self.user)
        VideoAnalysisListView.as_view()(request)

        request = self.factory.get("/api/analysis/")
        force_authenticate(request, user=self.user)
        response: Response = VideoAnalysisListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertIsInstance(response.data["results"], list)
        self.assertGreater(len(response.data["results"]), 0)

    def test_update_analysis_feedback(self) -> None:
        video_file: SimpleUploadedFile = self._create_video_file()
        request: Request = self.factory.post(
            "/api/analysis/",
            {"description": "feedback_test.mp4", "video": video_file},
            format="multipart",
        )
        force_authenticate(request, user=self.user)
        create_response: Response = VideoAnalysisListView.as_view()(request)

        self.assertEqual(create_response.status_code, 201)
        analysis_id = create_response.data["id"]

        update_data: dict[str, str] = {
            "actual_substance": "cocaine",
            "user_feedback": "This is unittest feedback",
        }

        request = self.factory.patch(
            f"/api/analysis/{analysis_id}/", update_data, format="json"
        )
        force_authenticate(request, user=self.user)
        response: Response = VideoAnalysisDetailView.as_view()(request, pk=analysis_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["actual_substance"], "cocaine")
        self.assertEqual(response.data["user_feedback"], "This is unittest feedback")


class TestAnalysisRetry(TestCase):
    cocaine: Substance
    morphine: Substance
    ethanol: Substance

    @classmethod
    def setUpTestData(cls) -> None:
        cls.cocaine = Substance.objects.create(name_en="cocaine")
        cls.morphine = Substance.objects.create(name_en="morphine")
        cls.ethanol = Substance.objects.create(name_en="ethanol")

    @classmethod
    def tearDownClass(cls) -> None:
        cleanup_test_media()
        super().tearDownClass()

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.user: User = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

    def tearDown(self) -> None:
        VideoAnalysis.objects.all().delete()
        User.objects.all().delete()

    def _create_video_file(self) -> SimpleUploadedFile:
        return SimpleUploadedFile(
            VIDEO_FILENAME, VIDEO_CONTENT, content_type=VIDEO_CONTENT_TYPE
        )

    def _create_failed_analysis(
        self, error_message, with_video=True, user=None
    ) -> VideoAnalysis:
        return VideoAnalysis.objects.create(
            user=user or self.user,
            description="Failed Analysis",
            video=self._create_video_file() if with_video else None,
            status=VideoAnalysis.Status.FAILED,
            error_message=error_message,
        )

    def test_can_retry_model_failed_analysis(self) -> None:
        analysis: VideoAnalysis = self._create_failed_analysis(
            "Model request failed: Connection timeout"
        )

        with patch("videoprocessor.tasks.process_video_task.delay") as mock_task:
            request: Request = self.factory.post(f"/api/analysis/{analysis.id}/retry/")
            force_authenticate(request, user=self.user)
            response: Response = VideoAnalysisRetryView.as_view()(
                request, pk=analysis.id
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn("message", response.data)
            self.assertEqual(response.data["analysis_id"], analysis.id)
            self.assertEqual(
                response.data["message"], "Analysis retry initiated successfully."
            )
            mock_task.assert_called_once_with(analysis.id)

            analysis.refresh_from_db()
            self.assertEqual(analysis.status, VideoAnalysis.Status.PENDING)
            self.assertIsNone(analysis.error_message)
            self.assertIsNone(analysis.completed_at)

    def test_cannot_retry_non_failed_analysis(self) -> None:
        analysis: VideoAnalysis = VideoAnalysis.objects.create(
            user=self.user,
            description="Completed Analysis",
            video=self._create_video_file(),
            status=VideoAnalysis.Status.COMPLETED,
            completed_at=timezone.now(),
        )

        request: Request = self.factory.post(f"/api/analysis/{analysis.id}/retry/")
        force_authenticate(request, user=self.user)
        response: Response = VideoAnalysisRetryView.as_view()(request, pk=analysis.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Only failed analyses can be retried.")

    def test_cannot_retry_without_video(self) -> None:
        analysis: VideoAnalysis = self._create_failed_analysis(
            "Model request failed: Timeout", with_video=False
        )

        request: Request = self.factory.post(f"/api/analysis/{analysis.id}/retry/")
        force_authenticate(request, user=self.user)
        response: Response = VideoAnalysisRetryView.as_view()(request, pk=analysis.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertEqual(
            response.data["error"],
            "Video file no longer exists. Cannot retry this analysis.",
        )

    @override_settings(VIDEO_LIFETIME_DAYS=14)
    def test_cannot_retry_old_analysis(self) -> None:
        lifetime_days = 14
        old_date = timezone.now() - timedelta(days=lifetime_days + 1)
        analysis: VideoAnalysis = self._create_failed_analysis(
            "Model request failed: Timeout"
        )
        VideoAnalysis.objects.filter(id=analysis.id).update(created_at=old_date)
        analysis.refresh_from_db()

        request: Request = self.factory.post(f"/api/analysis/{analysis.id}/retry/")
        force_authenticate(request, user=self.user)
        response: Response = VideoAnalysisRetryView.as_view()(request, pk=analysis.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertIn("too old to retry", response.data["error"])
        self.assertIn(str(lifetime_days), response.data["error"])

    def test_retry_clears_previous_results(self) -> None:
        analysis: VideoAnalysis = self._create_failed_analysis(
            "Model request failed: Timeout"
        )
        AnalysisResult.objects.create(
            analysis=analysis, substance=self.cocaine, confidence_score=0.8
        )
        AnalysisResult.objects.create(
            analysis=analysis, substance=self.morphine, confidence_score=0.2
        )

        self.assertEqual(analysis.analysis_results.count(), 2)

        with patch("videoprocessor.tasks.process_video_task.delay"):
            request: Request = self.factory.post(f"/api/analysis/{analysis.id}/retry/")
            force_authenticate(request, user=self.user)
            response: Response = VideoAnalysisRetryView.as_view()(
                request, pk=analysis.id
            )

            self.assertEqual(response.status_code, 200)
            analysis.refresh_from_db()
            self.assertEqual(analysis.analysis_results.count(), 0)

    def test_retry_requires_authentication(self) -> None:
        analysis: VideoAnalysis = self._create_failed_analysis(
            "Model request failed: Timeout"
        )

        from django.contrib.auth.models import AnonymousUser

        request: Request = self.factory.post(f"/api/analysis/{analysis.id}/retry/")
        request.user = AnonymousUser()
        response: Response = VideoAnalysisRetryView.as_view()(request, pk=analysis.id)

        self.assertEqual(response.status_code, 401)

    def test_retry_only_own_analysis(self) -> None:
        other_user: User = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password=TEST_PASSWORD,
        )
        analysis: VideoAnalysis = self._create_failed_analysis(
            "Model request failed: Timeout", user=other_user
        )

        request: Request = self.factory.post(f"/api/analysis/{analysis.id}/retry/")
        force_authenticate(request, user=self.user)
        response: Response = VideoAnalysisRetryView.as_view()(request, pk=analysis.id)

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)
        self.assertEqual(
            response.data["error"],
            "Analysis not found or you do not have permission to access it.",
        )

    def test_error_message_in_serializer(self) -> None:
        expected_error = "Model request failed: Connection timeout"
        analysis: VideoAnalysis = self._create_failed_analysis(expected_error)

        request: Request = self.factory.get(f"/api/analysis/{analysis.id}/")
        force_authenticate(request, user=self.user)
        response: Response = VideoAnalysisDetailView.as_view()(request, pk=analysis.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn("error_message", response.data)
        self.assertEqual(response.data["error_message"], expected_error)

    def test_retry_nonexistent_analysis(self) -> None:
        nonexistent_id = 99999
        request: Request = self.factory.post(f"/api/analysis/{nonexistent_id}/retry/")
        force_authenticate(request, user=self.user)
        response: Response = VideoAnalysisRetryView.as_view()(
            request, pk=nonexistent_id
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)


if __name__ == "__main__":
    success = run_tests([TestVideoAnalysis])
    sys.exit(0 if success else 1)
