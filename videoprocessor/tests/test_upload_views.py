from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.base import ContentFile
from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase
from rest_framework import status
from accounts.models import User
from analysis.models import VideoAnalysis, Substance
from videoprocessor.views.upload import VideoUploadView
from tests.common import TestFixtures, cleanup_test_media


VIDEO_CONTENT = b"fake video content for testing"
VIDEO_FILENAME = "test_video.mp4"
VIDEO_CONTENT_TYPE = "video/mp4"
TEST_PASSWORD = "testpass123"


class TestVideoUploadView(APITestCase):
    """Test VideoUploadView with dependency injection."""

    @classmethod
    def tearDownClass(cls):
        cleanup_test_media()
        super().tearDownClass()

    def setUp(self):
        self.factory = APIRequestFactory()
        user_data = TestFixtures.get_test_user_data()
        self.user = User.objects.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=TEST_PASSWORD,
        )

    def tearDown(self):
        VideoAnalysis.objects.all().delete()
        User.objects.all().delete()

    def _create_video_file(self):
        return SimpleUploadedFile(
            VIDEO_FILENAME, VIDEO_CONTENT, content_type=VIDEO_CONTENT_TYPE
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch(
        "videoprocessor.services.video_file_manager.VideoFileManager.extract_and_save_first_frame"
    )
    @patch("requests.post")
    def test_upload_with_default_video_manager(self, mock_requests_post, mock_extract):
        """Should work with default VideoFileManager and make request to ML endpoint."""
        mock_extract.return_value = ("test_thumb.jpg", ContentFile(b"fake thumbnail"))

        # Mock the ML endpoint response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "predictions": {"cocaine": 85.5, "morphine": 10.2, "ethanol": 4.3}
        }
        mock_requests_post.return_value = mock_response

        video_file = self._create_video_file()

        request = self.factory.post(
            reverse("videoprocessor:video-upload"),
            {"description": "test upload", "video": video_file},
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        response = VideoUploadView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("analysis_id", response.data)
        # Verify ML endpoint was called
        mock_requests_post.assert_called_once()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch(
        "videoprocessor.services.video_file_manager.VideoFileManager.extract_and_save_first_frame"
    )
    @patch("requests.post")
    def test_upload_with_injected_video_manager(self, mock_requests_post, mock_extract):
        """Should accept injected VideoFileManager and process with real ML service."""
        mock_extract.return_value = (
            "test_thumb.jpg",
            ContentFile(b"fake thumbnail"),
        )

        # Mock the ML endpoint response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "predictions": {"cocaine": 85.5, "morphine": 10.2}
        }
        mock_requests_post.return_value = mock_response

        video_file = self._create_video_file()

        request = self.factory.post(
            reverse("videoprocessor:video-upload"),
            {"description": "test upload", "video": video_file},
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        response = VideoUploadView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_extract.assert_called_once()
        mock_requests_post.assert_called_once()

    def test_upload_without_video_file(self):
        """Should return 400 when no video file provided."""
        request = self.factory.post(
            reverse("videoprocessor:video-upload"),
            {"description": "no video"},
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        response = VideoUploadView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_upload_with_invalid_patient_guid(self):
        """Should return 400 when patient_guid is invalid UUID."""
        video_file = self._create_video_file()

        request = self.factory.post(
            reverse("videoprocessor:video-upload"),
            {
                "description": "test",
                "video": video_file,
                "patient_guid": "not-a-uuid",
            },
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        response = VideoUploadView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid Patient GUID", response.data["error"])

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch(
        "videoprocessor.services.video_file_manager.VideoFileManager.extract_and_save_first_frame"
    )
    @patch(
        "videoprocessor.services.video_upload_service.patient_service.get_patient_by_guid"
    )
    @patch("requests.post")
    def test_upload_with_valid_patient_guid(
        self, mock_requests_post, mock_get_patient, mock_extract
    ):
        """Should accept valid patient GUID."""
        mock_extract.return_value = ("test_thumb.jpg", ContentFile(b"fake thumbnail"))
        mock_get_patient.return_value = {
            "id": "00000000-0000-0000-0000-000000000001",
            "first_name": "John",
            "last_name": "Doe",
        }

        # Mock the ML endpoint response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "predictions": {"cocaine": 85.5, "morphine": 10.2}
        }
        mock_requests_post.return_value = mock_response

        video_file = self._create_video_file()

        request = self.factory.post(
            reverse("videoprocessor:video-upload"),
            {
                "description": "test",
                "video": video_file,
                "patient_guid": "00000000-0000-0000-0000-000000000001",
            },
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        response = VideoUploadView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_get_patient.assert_called_once_with("00000000-0000-0000-0000-000000000001")
        mock_requests_post.assert_called_once()

    @patch(
        "videoprocessor.services.video_upload_service.patient_service.get_patient_by_guid"
    )
    def test_upload_with_nonexistent_patient(self, mock_get_patient):
        """Should return 404 when patient not found."""
        mock_get_patient.return_value = None

        video_file = self._create_video_file()

        request = self.factory.post(
            reverse("videoprocessor:video-upload"),
            {
                "description": "test",
                "video": video_file,
                "patient_guid": "00000000-0000-0000-0000-000000000001",
            },
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        response = VideoUploadView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(
        "videoprocessor.services.video_file_manager.VideoFileManager.extract_and_save_first_frame"
    )
    def test_upload_file_too_large(self, mock_extract):
        """Should return 400 when file exceeds size limit."""
        mock_extract.return_value = ("test_thumb.jpg", ContentFile(b"fake thumbnail"))

        # Create mock file with size exceeding limit
        video_file = self._create_video_file()

        request = self.factory.post(
            reverse("videoprocessor:video-upload"),
            {"description": "large file", "video": video_file},
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        # Mock the size to be over 3GB after the request is created
        request.FILES["video"].size = 4 * 1024**3

        response = VideoUploadView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("too large", response.data["error"])

    def test_upload_unsupported_format(self):
        """Should return 400 for non-MP4 files."""
        video_file = SimpleUploadedFile(
            "test_video.avi", VIDEO_CONTENT, content_type="video/avi"
        )

        request = self.factory.post(
            reverse("videoprocessor:video-upload"),
            {"description": "wrong format", "video": video_file},
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        response = VideoUploadView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unsupported file format", response.data["error"])

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch(
        "videoprocessor.services.video_file_manager.VideoFileManager.extract_and_save_first_frame"
    )
    @patch("requests.post")
    def test_upload_triggers_background_task(self, mock_requests_post, mock_extract):
        """Should process video with ML service after successful upload."""
        mock_extract.return_value = ("test_thumb.jpg", ContentFile(b"fake thumbnail"))

        # Mock the ML endpoint response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "predictions": {"cocaine": 85.5, "morphine": 10.2}
        }
        mock_requests_post.return_value = mock_response

        video_file = self._create_video_file()

        request = self.factory.post(
            reverse("videoprocessor:video-upload"),
            {"description": "test", "video": video_file},
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        response = VideoUploadView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify ML endpoint was called
        mock_requests_post.assert_called_once()
        # Check that analysis was created with results
        analysis_id = response.data["analysis_id"]
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        self.assertEqual(analysis.status, VideoAnalysis.Status.COMPLETED)
        self.assertEqual(analysis.analysis_results.count(), 2)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch(
        "videoprocessor.services.video_file_manager.VideoFileManager.extract_and_save_first_frame"
    )
    @patch("requests.post")
    def test_upload_handles_ml_service_error(self, mock_requests_post, mock_extract):
        """Should mark analysis as FAILED when ML service returns error."""
        mock_extract.return_value = ("test_thumb.jpg", ContentFile(b"fake thumbnail"))

        # Mock ML endpoint error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests_post.return_value = mock_response

        video_file = self._create_video_file()

        request = self.factory.post(
            reverse("videoprocessor:video-upload"),
            {"description": "test", "video": video_file},
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        response = VideoUploadView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Check that analysis was marked as FAILED
        analysis_id = response.data["analysis_id"]
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        self.assertEqual(analysis.status, VideoAnalysis.Status.FAILED)
        self.assertIsNotNone(analysis.error_message)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch(
        "videoprocessor.services.video_file_manager.VideoFileManager.extract_and_save_first_frame"
    )
    @patch("requests.post")
    def test_upload_handles_ml_service_request_exception(
        self, mock_requests_post, mock_extract
    ):
        """Should mark analysis as FAILED when ML service request fails."""
        mock_extract.return_value = ("test_thumb.jpg", ContentFile(b"fake thumbnail"))

        # Mock request exception
        mock_requests_post.side_effect = Exception("Network error")

        video_file = self._create_video_file()

        request = self.factory.post(
            reverse("videoprocessor:video-upload"),
            {"description": "test", "video": video_file},
            format="multipart",
        )
        force_authenticate(request, user=self.user)

        response = VideoUploadView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Check that analysis was marked as FAILED
        analysis_id = response.data["analysis_id"]
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        self.assertEqual(analysis.status, VideoAnalysis.Status.FAILED)
        self.assertIsNotNone(analysis.error_message)
