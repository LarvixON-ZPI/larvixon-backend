import sys
import os
from unittest.mock import patch
from datetime import timedelta
from typing import Any, Optional, TYPE_CHECKING
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.http import HttpResponse
from rest_framework.test import APIClient
from django.test.client import Client

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse

from tests.common import run_tests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "larvixon_site.settings")

import django

django.setup()

from accounts.models import User
from analysis.models import VideoAnalysis, Substance, AnalysisResult
from videoprocessor.tasks import process_video_task

VIDEO_CONTENT = b"fake video content for testing"
VIDEO_FILENAME = "test_video.mp4"
VIDEO_CONTENT_TYPE = "video/mp4"
TEST_PASSWORD = "testpass123"

CONFIDENCE_COCAINE = 0.85
CONFIDENCE_MORPHINE = 0.10
CONFIDENCE_ETHANOL = 0.05
EXPECTED_SUBSTANCES_COUNT = 3


class TestAnalysisRetry(TestCase):
    """Test suite for video analysis retry functionality."""

    cocaine: Substance
    morphine: Substance
    ethanol: Substance

    @classmethod
    def setUpTestData(cls) -> None:
        """Set up data for the whole TestCase."""
        # Create substances that are referenced in tests
        cls.cocaine = Substance.objects.create(name_en="cocaine")
        cls.morphine = Substance.objects.create(name_en="morphine")
        cls.ethanol = Substance.objects.create(name_en="ethanol")

    def setUp(self) -> None:
        """Set up test fixtures before each test method."""
        self.test_user: User = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.test_user)

    def tearDown(self) -> None:
        for analysis in VideoAnalysis.objects.all():
            analysis.delete()

        User.objects.all().delete()

    def _create_video_file(self) -> SimpleUploadedFile:
        """Create a fresh video file for testing.

        Returns:
            A new SimpleUploadedFile instance for each call.
        """
        return SimpleUploadedFile(
            VIDEO_FILENAME, VIDEO_CONTENT, content_type=VIDEO_CONTENT_TYPE
        )

    def _create_failed_analysis(
        self,
        error_message: str = "Model request failed: Connection timeout",
        with_video: bool = True,
        user: Optional[User] = None,
    ) -> VideoAnalysis:
        """Helper to create a failed analysis for testing.

        Args:
            error_message: The error message to set on the analysis.
            with_video: Whether to include a video file.
            user: The user who owns the analysis (defaults to self.test_user).

        Returns:
            A VideoAnalysis instance with FAILED status.
        """
        return VideoAnalysis.objects.create(
            user=user or self.test_user,
            title="Failed Analysis",
            video=self._create_video_file() if with_video else None,
            status=VideoAnalysis.Status.FAILED,
            error_message=error_message,
        )

    def _retry_analysis(self, analysis_id: int) -> Any:
        return self.client.post(f"/api/analysis/{analysis_id}/retry/")

    def _get_analysis(self, analysis_id: int) -> Any:
        return self.client.get(f"/api/analysis/{analysis_id}/")

    def test_can_retry_model_failed_analysis(self) -> None:
        """Test that an analysis with model failure can be retried.

        Verifies that a failed analysis with a model-related error can be
        retried successfully, resetting its status to PENDING and clearing
        the error message.
        """
        analysis = self._create_failed_analysis(
            error_message="Model request failed: Connection timeout"
        )

        with patch("videoprocessor.tasks.process_video_task.delay") as mock_task:
            response = self._retry_analysis(analysis.id)

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
        """Test that a completed analysis cannot be retried.

        Only analyses with FAILED status should be retryable.
        """
        analysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Completed Analysis",
            video=self._create_video_file(),
            status=VideoAnalysis.Status.COMPLETED,
            completed_at=timezone.now(),
        )

        response = self._retry_analysis(analysis.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Only failed analyses can be retried.")

    def test_cannot_retry_non_model_failure(self) -> None:
        """Test that analysis with non-model errors cannot be retried.

        Only model-related failures (error_message starts with 'Model request failed')
        should be retryable.
        """
        analysis = self._create_failed_analysis(
            error_message="Database error: Connection lost"
        )

        response = self._retry_analysis(analysis.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertEqual(
            response.data["error"],
            "This analysis cannot be retried. Only analyses that failed due to model-related errors can be retried.",
        )

    def test_cannot_retry_without_video(self) -> None:
        """Test that analysis without video file cannot be retried.

        Video file is required for retry since it needs to be reprocessed.
        """
        analysis = self._create_failed_analysis(
            error_message="Model request failed: Timeout", with_video=False
        )

        response = self._retry_analysis(analysis.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertEqual(
            response.data["error"],
            "Video file no longer exists. Cannot retry this analysis.",
        )

    @override_settings(VIDEO_LIFETIME_DAYS=14)
    def test_cannot_retry_old_analysis(self) -> None:
        """Test that analyses older than VIDEO_LIFETIME_DAYS cannot be retried.

        This prevents retry attempts on analyses where the video file may have
        been cleaned up due to age.
        """
        lifetime_days = 14
        old_date = timezone.now() - timedelta(days=lifetime_days + 1)
        analysis = self._create_failed_analysis(
            error_message="Model request failed: Timeout"
        )

        VideoAnalysis.objects.filter(id=analysis.id).update(created_at=old_date)
        analysis.refresh_from_db()

        response = self._retry_analysis(analysis.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertIn("too old to retry", response.data["error"])
        self.assertIn(str(lifetime_days), response.data["error"])

    def test_retry_clears_previous_results(self) -> None:
        """Test that retry clears previous analysis results.

        When retrying, any stale results from the failed attempt should be
        removed to avoid confusion with new results.
        """
        analysis = self._create_failed_analysis(
            error_message="Model request failed: Timeout"
        )

        AnalysisResult.objects.create(
            analysis=analysis, substance=self.cocaine, confidence_score=0.8
        )
        AnalysisResult.objects.create(
            analysis=analysis, substance=self.morphine, confidence_score=0.2
        )

        self.assertEqual(analysis.analysis_results.count(), 2)

        with patch("videoprocessor.tasks.process_video_task.delay"):
            response = self._retry_analysis(analysis.id)

            self.assertEqual(response.status_code, 200)

            # Verify results were cleared
            analysis.refresh_from_db()
            self.assertEqual(analysis.analysis_results.count(), 0)

    def test_retry_requires_authentication(self) -> None:
        """Test that retry endpoint requires authentication.

        Unauthenticated requests should be rejected.
        """
        analysis = self._create_failed_analysis(
            error_message="Model request failed: Timeout"
        )

        unauthenticated_client = APIClient()
        response = unauthenticated_client.post(f"/api/analysis/{analysis.id}/retry/")

        self.assertEqual(response.status_code, 401)

    def test_retry_only_own_analysis(self) -> None:
        """Test that user can only retry their own analyses.

        Users should not be able to access or retry analyses belonging to others.
        """
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password=TEST_PASSWORD,
        )

        # Create analysis for other user
        analysis = self._create_failed_analysis(
            error_message="Model request failed: Timeout", user=other_user
        )

        # Try to retry as self.test_user
        response = self._retry_analysis(analysis.id)

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)
        self.assertEqual(
            response.data["error"],
            "Analysis not found or you do not have permission to access it.",
        )

    def test_error_message_in_serializer(self) -> None:
        """Test that error_message is included in API response.

        The error_message field should be exposed in the API to help users
        understand why an analysis failed.
        """
        expected_error = "Model request failed: Connection timeout"
        analysis = self._create_failed_analysis(error_message=expected_error)

        response = self._get_analysis(analysis.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn("error_message", response.data)
        self.assertEqual(response.data["error_message"], expected_error)

    def test_retry_nonexistent_analysis(self) -> None:
        """Test that retrying a non-existent analysis returns 404.

        Edge case: user attempts to retry an analysis that doesn't exist.
        """
        nonexistent_id = 99999
        response = self._retry_analysis(nonexistent_id)

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)


class TestProcessVideoTask(TestCase):
    """Test suite for process_video_task functionality."""

    cocaine: Substance
    morphine: Substance
    ethanol: Substance

    @classmethod
    def setUpTestData(cls) -> None:
        """Set up data for the whole TestCase."""
        cls.cocaine = Substance.objects.create(name_en="cocaine")
        cls.morphine = Substance.objects.create(name_en="morphine")
        cls.ethanol = Substance.objects.create(name_en="ethanol")

    def setUp(self) -> None:
        """Set up test fixtures before each test method."""
        self.test_user: User = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

    def tearDown(self) -> None:
        """Clean up after each test method."""
        VideoAnalysis.objects.all().delete()
        User.objects.all().delete()

    def _create_video_file(self) -> SimpleUploadedFile:
        """Create a fresh video file for testing."""
        return SimpleUploadedFile(
            VIDEO_FILENAME, VIDEO_CONTENT, content_type=VIDEO_CONTENT_TYPE
        )

    @patch("videoprocessor.tasks.send_video_to_ml")
    def test_process_video_task_success(self, mock_ml) -> None:
        """Test process_video_task with successful ML model response.

        Verifies that when the ML model returns valid results, the task
        correctly creates AnalysisResult objects and marks the analysis
        as COMPLETED.
        """
        mock_ml.return_value = {
            "cocaine": CONFIDENCE_COCAINE,
            "morphine": CONFIDENCE_MORPHINE,
            "ethanol": CONFIDENCE_ETHANOL,
        }

        analysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Test Analysis",
            video=self._create_video_file(),
            status=VideoAnalysis.Status.PENDING,
        )

        process_video_task(analysis.id)

        analysis.refresh_from_db()
        self.assertEqual(analysis.status, VideoAnalysis.Status.COMPLETED)
        self.assertIsNotNone(analysis.completed_at)
        self.assertIsNone(analysis.error_message)

        results = analysis.analysis_results.all()
        self.assertEqual(results.count(), EXPECTED_SUBSTANCES_COUNT)

        result = AnalysisResult.objects.get(analysis=analysis, substance=self.cocaine)
        self.assertEqual(result.confidence_score, CONFIDENCE_COCAINE)

    @patch("videoprocessor.tasks.send_video_to_ml")
    def test_process_video_task_ml_returns_none(self, mock_ml) -> None:
        """Test process_video_task when ML model returns None.

        When the ML service fails and returns None, the task should mark
        the analysis as FAILED with an appropriate error message.
        """
        mock_ml.return_value = None

        analysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Test Analysis",
            video=self._create_video_file(),
            status=VideoAnalysis.Status.PENDING,
        )

        process_video_task(analysis.id)

        analysis.refresh_from_db()
        self.assertEqual(analysis.status, VideoAnalysis.Status.FAILED)
        self.assertIsNotNone(analysis.error_message)
        self.assertTrue(analysis.error_message.startswith("Model request failed"))

    @patch("videoprocessor.tasks.send_video_to_ml")
    def test_process_video_task_ml_raises_exception(self, mock_ml) -> None:
        """Test process_video_task when ML model raises an exception.

        When the ML service raises an exception, the task should catch it
        and mark the analysis as FAILED with a model-related error message
        that allows for retry.
        """
        mock_ml.side_effect = Exception("Network error")

        analysis = VideoAnalysis.objects.create(
            user=self.test_user,
            title="Test Analysis",
            video=self._create_video_file(),
            status=VideoAnalysis.Status.PENDING,
        )

        process_video_task(analysis.id)

        analysis.refresh_from_db()
        self.assertEqual(analysis.status, VideoAnalysis.Status.FAILED)
        self.assertIsNotNone(analysis.error_message)
        self.assertIn("Model request failed", analysis.error_message)


if __name__ == "__main__":
    success = run_tests([TestAnalysisRetry, TestProcessVideoTask])
    sys.exit(0 if success else 1)
