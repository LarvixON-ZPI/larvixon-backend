import os
import tempfile
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from analysis.models import VideoAnalysis, Substance
from videoprocessor.tasks import process_video_task
from videoprocessor.services.video_processing_service import VideoProcessingService
from tests.common import TestFixtures, cleanup_test_media


VIDEO_CONTENT = b"fake video content for testing"
TEST_PASSWORD = "testpass123"


class TestGetSortedPredictions(TestCase):
    """Test the get_sorted_predictions helper function."""

    def test_returns_sorted_predictions(self):
        """Should return predictions sorted by confidence descending."""
        scores = {
            "cocaine": 45.0,
            "morphine": 85.0,
            "ethanol": 20.0,
        }

        result = VideoProcessingService.get_sorted_predictions(scores)

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], ("morphine", 85.0))
        self.assertEqual(result[1], ("cocaine", 45.0))
        self.assertEqual(result[2], ("ethanol", 20.0))

    def test_returns_empty_list_for_none(self):
        """Should return empty list when scores is None."""
        result = VideoProcessingService.get_sorted_predictions(None)
        self.assertEqual(result, [])

    def test_returns_empty_list_for_empty_dict(self):
        """Should return empty list when scores is empty."""
        result = VideoProcessingService.get_sorted_predictions({})
        self.assertEqual(result, [])


class TestProcessVideoTask(TestCase):
    """Test the process_video_task Celery task."""

    @classmethod
    def tearDownClass(cls):
        cleanup_test_media()
        super().tearDownClass()

    def setUp(self):
        user_data = TestFixtures.get_test_user_data()
        self.user = User.objects.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=TEST_PASSWORD,
        )

        # Create a video analysis
        video_file = SimpleUploadedFile(
            "test_video.mp4", VIDEO_CONTENT, content_type="video/mp4"
        )

        self.analysis = VideoAnalysis.objects.create(
            user=self.user,
            description="Test analysis",
        )
        self.analysis.video.save("test_video.mp4", video_file, save=True)

    def tearDown(self):
        VideoAnalysis.objects.all().delete()
        User.objects.all().delete()

    def test_task_with_nonexistent_analysis_id(self):
        """Should handle nonexistent analysis gracefully."""
        # Should not raise exception
        process_video_task(99999)

        # Analysis should not exist
        self.assertFalse(VideoAnalysis.objects.filter(id=99999).exists())

    @patch("videoprocessor.services.video_processing_service.ml_service")
    def test_task_updates_status_to_pending(self, mock_ml_service):
        """Should set status to PENDING when task starts."""
        mock_ml_service.predict_video.return_value = {
            "cocaine": 90.0,
            "morphine": 10.0,
        }

        initial_status = self.analysis.status
        process_video_task(self.analysis.id)

        self.analysis.refresh_from_db()
        # Status should eventually be COMPLETED after successful processing
        self.assertEqual(self.analysis.status, VideoAnalysis.Status.COMPLETED)

    @patch("videoprocessor.services.video_processing_service.ml_service")
    def test_task_successful_prediction(self, mock_ml_service):
        """Should create analysis results for successful prediction."""
        mock_ml_service.predict_video.return_value = {
            "cocaine": 85.5,
            "morphine": 10.2,
            "ethanol": 4.3,
        }

        process_video_task(self.analysis.id)

        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.status, VideoAnalysis.Status.COMPLETED)
        self.assertIsNotNone(self.analysis.completed_at)
        self.assertIsNone(self.analysis.error_message)

        # Check analysis results were created
        results = self.analysis.analysis_results.all()
        self.assertEqual(results.count(), 3)

        # Check results are sorted by confidence
        result_list = list(results.order_by("-confidence_score"))
        self.assertEqual(result_list[0].substance.name_en, "cocaine")
        self.assertEqual(result_list[0].confidence_score, 85.5)

    @patch("videoprocessor.services.video_processing_service.ml_service")
    def test_task_creates_substances_if_not_exist(self, mock_ml_service):
        """Should create Substance objects if they don't exist."""
        mock_ml_service.predict_video.return_value = {
            "new_substance_xyz": 90.0,
        }

        initial_count = Substance.objects.count()
        process_video_task(self.analysis.id)

        # Should have created new substance
        self.assertEqual(Substance.objects.count(), initial_count + 1)
        self.assertTrue(Substance.objects.filter(name_en="new_substance_xyz").exists())

    @patch("videoprocessor.services.video_processing_service.ml_service")
    def test_task_failed_prediction_no_results(self, mock_ml_service):
        """Should mark as FAILED when prediction returns None."""
        mock_ml_service.predict_video.return_value = None

        process_video_task(self.analysis.id)

        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.status, VideoAnalysis.Status.FAILED)
        self.assertIsNotNone(self.analysis.error_message)
        self.assertIn("No predictions returned", self.analysis.error_message)

    @patch("videoprocessor.services.video_processing_service.ml_service")
    def test_task_handles_exception(self, mock_ml_service):
        """Should mark as FAILED and log error on exception."""
        mock_ml_service.predict_video.side_effect = Exception("ML service error")

        process_video_task(self.analysis.id)

        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.status, VideoAnalysis.Status.FAILED)
        self.assertIsNotNone(self.analysis.error_message)
        self.assertIn("ML service error", self.analysis.error_message)

    @patch("videoprocessor.services.video_processing_service.ml_service")
    @patch("videoprocessor.services.video_processing_service.os.remove")
    def test_task_cleans_up_temp_file(self, mock_remove, mock_ml_service):
        """Should clean up temporary file after processing."""
        mock_ml_service.predict_video.return_value = {"cocaine": 90.0}

        process_video_task(self.analysis.id)

        # Verify temp file cleanup was called
        mock_remove.assert_called()

    @patch("videoprocessor.services.video_processing_service.ml_service")
    @patch("videoprocessor.services.video_processing_service.os.remove")
    def test_task_cleans_up_temp_file_on_error(self, mock_remove, mock_ml_service):
        """Should clean up temp file even when processing fails."""
        mock_ml_service.predict_video.side_effect = Exception("Error")

        process_video_task(self.analysis.id)

        # Verify cleanup was attempted
        mock_remove.assert_called()

    @patch("videoprocessor.services.video_processing_service.ml_service")
    def test_task_clears_previous_error_message(self, mock_ml_service):
        """Should clear error_message when reprocessing."""
        mock_ml_service.predict_video.return_value = {"cocaine": 90.0}

        # Set initial error
        self.analysis.error_message = "Previous error"
        self.analysis.save()

        process_video_task(self.analysis.id)

        self.analysis.refresh_from_db()
        self.assertIsNone(self.analysis.error_message)
        self.assertEqual(self.analysis.status, VideoAnalysis.Status.COMPLETED)
