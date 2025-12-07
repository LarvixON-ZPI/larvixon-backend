import tempfile
import cv2
import logging
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import os
from django.core.files.storage import Storage

logger: logging.Logger = logging.getLogger(__name__)

THUMBNAIL_FILENAME_SUFFIX = "_thumb.jpg"


class VideoFileManager:
    """
    Manages the saving of video files and extraction of thumbnails.
    Uses Django's storage backend (injectable for testing).
    """

    def __init__(self, storage: Storage | None = None):
        self.fs = storage or default_storage

    def save_video_file(self, video_file):
        try:
            filename = self.fs.save(video_file.name, video_file)
            video_path = (
                self.fs.path(filename) if hasattr(self.fs, "path") else filename
            )
            return filename, video_path

        except Exception as e:
            logger.exception(f"Failed to save video file {video_file.name}: {e}")
            raise IOError(f"Failed to save video file: {e}")

    def extract_and_save_first_frame(self, video_file):
        """
        Extracts the first frame from the video path and saves it as a thumbnail
        """

        temp_path = None
        try:
            suffix = os.path.splitext(video_file.name)[1]

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_f:
                for chunk in video_file.chunks():
                    temp_f.write(chunk)
                temp_path = temp_f.name

            cap = cv2.VideoCapture(temp_path)
            if not cap.isOpened():
                raise IOError("Could not open video file for frame extraction.")

            ret, frame = cap.read()
            cap.release()
            if not ret:
                raise IOError("Could not read first frame from video.")

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
            is_success, buffer = cv2.imencode(".jpg", frame, encode_param)
            if not is_success:
                raise IOError("Failed to encode frame to JPEG.")

            content_file = ContentFile(buffer.tobytes())
            base_name, _ = os.path.splitext(video_file.name)
            thumbnail_name = base_name + THUMBNAIL_FILENAME_SUFFIX

            return thumbnail_name, content_file

        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
