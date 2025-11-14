import unittest
import sys
import os
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import timedelta
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from tests.common import run_tests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "larvixon_site.settings")

import django

django.setup()

from accounts.models import User
from analysis.models import VideoAnalysis, Substance, AnalysisResult
from videoprocessor.tasks import process_video_task


class TestAnalysisRetry(TestCase):
    def setUp(self) -> None:
        self.test_user: User = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

        self.video_content = b"fake video content for testing"
        self.video_file = SimpleUploadedFile(
            "test_video.mp4", self.video_content, content_type="video/mp4"
        )

    def tearDown(self) -> None:
        for analysis in VideoAnalysis.objects.all():
            analysis.delete()

        User.objects.all().delete()

    def test_can_retry_model_failed_analysis(self) -> None:
        """Test that an analysis with model failure can be retried."""
        analysis: VideoAnalysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Failed Analysis",
            video=self.video_file,
            status=VideoAnalysis.Status.FAILED,
            error_message="Model request failed: Connection timeout",
        )

        with patch("videoprocessor.tasks.process_video_task.delay") as mock_task:
            from rest_framework.test import APIClient

            client = APIClient()
            client.force_authenticate(user=self.test_user)
            response = client.post(f"/api/analysis/{analysis.id}/retry/")

            self.assertEqual(response.status_code, 200)
            self.assertIn("message", response.data)
            self.assertEqual(response.data["analysis_id"], analysis.id)

            mock_task.assert_called_once_with(analysis.id)

            analysis.refresh_from_db()
            self.assertEqual(analysis.status, VideoAnalysis.Status.PENDING)
            self.assertIsNone(analysis.error_message)
            self.assertIsNone(analysis.completed_at)

    def test_cannot_retry_non_failed_analysis(self) -> None:
        """Test that a completed analysis cannot be retried."""
        analysis: VideoAnalysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Completed Analysis",
            video=self.video_file,
            status=VideoAnalysis.Status.COMPLETED,
            completed_at=timezone.now(),
        )

        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.test_user)
        response = client.post(f"/api/analysis/{analysis.id}/retry/")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertIn("Only failed analyses", response.data["error"])

    def test_cannot_retry_non_model_failure(self) -> None:
        """Test that analysis with non-model errors cannot be retried."""
        analysis: VideoAnalysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Failed Analysis",
            video=self.video_file,
            status=VideoAnalysis.Status.FAILED,
            error_message="Database error: Connection lost",
        )

        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.test_user)
        response = client.post(f"/api/analysis/{analysis.id}/retry/")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertIn("model-related errors", response.data["error"])

    def test_cannot_retry_without_video(self) -> None:
        """Test that analysis without video file cannot be retried."""
        analysis: VideoAnalysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Failed Analysis",
            video=None,
            status=VideoAnalysis.Status.FAILED,
            error_message="Model request failed: Timeout",
        )

        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.test_user)
        response = client.post(f"/api/analysis/{analysis.id}/retry/")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertIn("Video file no longer exists", response.data["error"])

    @override_settings(VIDEO_LIFETIME_DAYS=14)
    def test_cannot_retry_old_analysis(self) -> None:
        """Test that analyses older than VIDEO_LIFETIME_DAYS cannot be retried."""
        old_date = timezone.now() - timedelta(days=150)
        analysis: VideoAnalysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Old Failed Analysis",
            video=self.video_file,
            status=VideoAnalysis.Status.FAILED,
            error_message="Model request failed: Timeout",
        )

        VideoAnalysis.objects.filter(id=analysis.id).update(created_at=old_date)
        analysis.refresh_from_db()

        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.test_user)
        response = client.post(f"/api/analysis/{analysis.id}/retry/")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertIn("too old to retry", response.data["error"])

    def test_retry_clears_previous_results(self) -> None:
        """Test that retry clears previous analysis results."""
        analysis: VideoAnalysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Failed Analysis with Results",
            video=self.video_file,
            status=VideoAnalysis.Status.FAILED,
            error_message="Model request failed: Timeout",
        )

        # Add some analysis results
        substance1 = Substance.objects.create(name_en="cocaine")
        substance2 = Substance.objects.create(name_en="morphine")
        AnalysisResult.objects.create(
            analysis=analysis, substance=substance1, confidence_score=0.8
        )
        AnalysisResult.objects.create(
            analysis=analysis, substance=substance2, confidence_score=0.2
        )

        self.assertEqual(analysis.analysis_results.count(), 2)

        with patch("videoprocessor.tasks.process_video_task.delay"):
            from rest_framework.test import APIClient

            client = APIClient()
            client.force_authenticate(user=self.test_user)
            response = client.post(f"/api/analysis/{analysis.id}/retry/")

            self.assertEqual(response.status_code, 200)

            # Verify results were cleared
            analysis.refresh_from_db()
            self.assertEqual(analysis.analysis_results.count(), 0)

    def test_retry_requires_authentication(self) -> None:
        """Test that retry endpoint requires authentication."""
        analysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Failed Analysis",
            video=self.video_file,
            status=VideoAnalysis.Status.FAILED,
            error_message="Model request failed: Timeout",
        )

        from rest_framework.test import APIClient

        client = APIClient()
        # Don't authenticate
        response = client.post(f"/api/analysis/{analysis.id}/retry/")

        self.assertEqual(response.status_code, 401)

    def test_retry_only_own_analysis(self) -> None:
        """Test that user can only retry their own analyses."""
        # Create another user
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123",
        )

        # Create analysis for other user
        analysis = VideoAnalysis.objects.create(
            user=other_user,
            title="Failed Analysis",
            video=self.video_file,
            status=VideoAnalysis.Status.FAILED,
            error_message="Model request failed: Timeout",
        )

        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.test_user)  # Authenticate as first user
        response = client.post(f"/api/analysis/{analysis.id}/retry/")

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)

    @patch("videoprocessor.tasks.send_video_to_ml")
    def test_process_video_task_with_mock_ml(self, mock_ml):
        """Test process_video_task with mocked ML model."""
        # Mock successful ML response
        mock_ml.return_value = {
            "cocaine": 0.85,
            "morphine": 0.10,
            "ethanol": 0.05,
        }

        analysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Test Analysis",
            video=self.video_file,
            status=VideoAnalysis.Status.PENDING,
        )

        # Process the video
        process_video_task(analysis.id)

        # Verify analysis was updated
        analysis.refresh_from_db()
        self.assertEqual(analysis.status, VideoAnalysis.Status.COMPLETED)
        self.assertIsNotNone(analysis.completed_at)
        self.assertIsNone(analysis.error_message)

        # Verify results were created
        results = analysis.analysis_results.all()
        self.assertEqual(results.count(), 3)

        # Verify substances were created
        cocaine = Substance.objects.get(name_en="cocaine")
        result = AnalysisResult.objects.get(analysis=analysis, substance=cocaine)
        self.assertEqual(result.confidence_score, 0.85)

    @patch("videoprocessor.tasks.send_video_to_ml")
    def test_process_video_task_with_ml_failure(self, mock_ml):
        """Test process_video_task when ML model fails."""
        # Mock ML failure (returns None)
        mock_ml.return_value = None

        analysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Test Analysis",
            video=self.video_file,
            status=VideoAnalysis.Status.PENDING,
        )

        # Process the video
        process_video_task(analysis.id)

        # Verify analysis was marked as failed
        analysis.refresh_from_db()
        self.assertEqual(analysis.status, VideoAnalysis.Status.FAILED)
        self.assertIsNotNone(analysis.error_message)
        self.assertTrue(analysis.error_message.startswith("Model request failed"))

    @patch("videoprocessor.tasks.send_video_to_ml")
    def test_process_video_task_with_exception(self, mock_ml):
        """Test process_video_task when an exception occurs."""
        # Mock ML raising an exception
        mock_ml.side_effect = Exception("Network error")

        analysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Test Analysis",
            video=self.video_file,
            status=VideoAnalysis.Status.PENDING,
        )

        # Process the video
        process_video_task(analysis.id)

        # Verify analysis was marked as failed with error message
        analysis.refresh_from_db()
        self.assertEqual(analysis.status, VideoAnalysis.Status.FAILED)
        self.assertIsNotNone(analysis.error_message)
        self.assertIn("Model request failed", analysis.error_message)

    def test_error_message_in_serializer(self) -> None:
        """Test that error_message is included in API response."""
        analysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Failed Analysis",
            video=self.video_file,
            status=VideoAnalysis.Status.FAILED,
            error_message="Model request failed: Connection timeout",
        )

        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.test_user)
        response = client.get(f"/api/analysis/{analysis.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("error_message", response.data)
        self.assertEqual(
            response.data["error_message"], "Model request failed: Connection timeout"
        )


if __name__ == "__main__":
    success = run_tests([TestAnalysisRetry])
    sys.exit(0 if success else 1)
