import os
import tempfile
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from videoprocessor.services import VideoFileManager


class TestVideoFileManager(TestCase):
    """Test VideoFileManager service."""

    def setUp(self):
        self.manager = VideoFileManager()
        # Create a simple test video file
        self.video_content = b"fake video content for testing"
        self.video_file = SimpleUploadedFile(
            "test_video.mp4",
            self.video_content,
            content_type="video/mp4",
        )

    def tearDown(self):
        # Clean up any files created during tests
        try:
            saved_filename = getattr(self, "saved_filename", None)
            if saved_filename:
                if default_storage.exists(saved_filename):
                    default_storage.delete(saved_filename)
        except Exception:
            pass

    def test_init_with_default_storage(self):
        """Should use default_storage when no storage provided."""
        manager = VideoFileManager()
        self.assertEqual(manager.fs, default_storage)

    def test_init_with_custom_storage(self):
        """Should use provided storage when given."""
        mock_storage = MagicMock()
        manager = VideoFileManager(storage=mock_storage)
        self.assertEqual(manager.fs, mock_storage)

    def test_init_with_none_storage_uses_default(self):
        """Should use default_storage when None is provided."""
        manager = VideoFileManager(storage=None)
        self.assertEqual(manager.fs, default_storage)

    @patch("videoprocessor.services.video_file_manager.default_storage")
    def test_save_video_file_success(self, mock_storage):
        """Should save video file and return filename and path."""
        mock_storage.save.return_value = "videos/test_video.mp4"
        mock_storage.path.return_value = "/media/videos/test_video.mp4"

        manager = VideoFileManager(storage=mock_storage)
        filename, video_path = manager.save_video_file(self.video_file)

        self.assertEqual(filename, "videos/test_video.mp4")
        self.assertEqual(video_path, "/media/videos/test_video.mp4")
        mock_storage.save.assert_called_once_with(self.video_file.name, self.video_file)

    @patch("videoprocessor.services.video_file_manager.default_storage")
    def test_save_video_file_without_path_attribute(self, mock_storage):
        """Should handle storage without path attribute."""
        mock_storage.save.return_value = "videos/test_video.mp4"
        mock_storage.path.side_effect = AttributeError()

        manager = VideoFileManager(storage=mock_storage)
        filename, video_path = manager.save_video_file(self.video_file)

        self.assertEqual(filename, "videos/test_video.mp4")
        self.assertEqual(video_path, "videos/test_video.mp4")

    @patch("videoprocessor.services.video_file_manager.default_storage")
    def test_save_video_file_handles_exception(self, mock_storage):
        """Should raise IOError when save fails."""
        mock_storage.save.side_effect = Exception("Storage error")

        manager = VideoFileManager(storage=mock_storage)

        with self.assertRaises(IOError) as context:
            manager.save_video_file(self.video_file)

        self.assertIn("Failed to save video file", str(context.exception))

    @patch("videoprocessor.services.video_file_manager.cv2.VideoCapture")
    def test_extract_and_save_first_frame_success(self, mock_video_capture):
        """Should extract first frame and return thumbnail info."""
        # Mock cv2 operations
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, b"fake frame data")
        mock_video_capture.return_value = mock_cap

        with patch(
            "videoprocessor.services.video_file_manager.cv2.imencode"
        ) as mock_imencode:
            mock_imencode.return_value = (True, b"fake jpeg data")

            # Reset file pointer
            self.video_file.seek(0)

            thumbnail_name, content_file = self.manager.extract_and_save_first_frame(
                self.video_file
            )

            self.assertEqual(thumbnail_name, "test_video_thumb.jpg")
            self.assertIsNotNone(content_file)
            mock_cap.release.assert_called_once()

    @patch("videoprocessor.services.video_file_manager.cv2.VideoCapture")
    def test_extract_first_frame_video_not_opened(self, mock_video_capture):
        """Should raise IOError when video cannot be opened."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap

        with self.assertRaises(IOError) as context:
            self.manager.extract_and_save_first_frame(self.video_file)

        self.assertIn("Could not open video file", str(context.exception))

    @patch("videoprocessor.services.video_file_manager.cv2.VideoCapture")
    def test_extract_first_frame_read_fails(self, mock_video_capture):
        """Should raise IOError when frame cannot be read."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_video_capture.return_value = mock_cap

        with self.assertRaises(IOError) as context:
            self.manager.extract_and_save_first_frame(self.video_file)

        self.assertIn("Could not read first frame", str(context.exception))
        mock_cap.release.assert_called_once()

    @patch("videoprocessor.services.video_file_manager.cv2.VideoCapture")
    def test_extract_first_frame_encode_fails(self, mock_video_capture):
        """Should raise IOError when frame encoding fails."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, b"fake frame")
        mock_video_capture.return_value = mock_cap

        with patch(
            "videoprocessor.services.video_file_manager.cv2.imencode"
        ) as mock_imencode:
            mock_imencode.return_value = (False, None)

            with self.assertRaises(IOError) as context:
                self.manager.extract_and_save_first_frame(self.video_file)

            self.assertIn("Failed to encode frame", str(context.exception))
            mock_cap.release.assert_called_once()

    @patch("videoprocessor.services.video_file_manager.cv2.VideoCapture")
    @patch("videoprocessor.services.video_file_manager.os.path.exists")
    @patch("videoprocessor.services.video_file_manager.os.unlink")
    def test_extract_first_frame_cleans_up_temp_file(
        self, mock_unlink, mock_exists, mock_video_capture
    ):
        """Should clean up temporary file even if processing fails."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap
        mock_exists.return_value = True

        try:
            self.manager.extract_and_save_first_frame(self.video_file)
        except IOError:
            pass

        # Verify temp file cleanup was attempted
        mock_unlink.assert_called()
