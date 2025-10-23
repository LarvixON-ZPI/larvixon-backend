import cv2
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage 
import os 
from django.core.files.storage import Storage

THUMBNAIL_FILENAME_SUFFIX = "_thumb.jpg"

class VideoFileManager:
    """
    Manages the saving of video files and extraction of thumbnails.
    Uses Django's default_storage backend.
    """

    def __init__(self, storage: Storage = default_storage):
        self.fs = storage
        
    def save_video_file(self, video_file):
        try:
            filename = self.fs.save(video_file.name, video_file)
            video_path = self.fs.path(filename) if hasattr(self.fs, 'path') else filename
            return filename, video_path

        except Exception as e:
            raise IOError(f"Failed to save video file: {e}")

    def extract_and_save_first_frame(self, video_path: str, video_filename: str):
        """
        Extracts the first frame from the video path and saves it as a thumbnail
        """

        base_name, _ = os.path.splitext(video_filename)
        thumbnail_name = base_name + THUMBNAIL_FILENAME_SUFFIX

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Could not open video file for frame extraction: {video_path}")

        ret, frame = cap.read()
        cap.release()

        if not ret:
            raise IOError("Could not read first frame from video.")

        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90] 
        is_success, buffer = cv2.imencode(".jpg", frame, encode_param)
        if not is_success:
            raise IOError("Failed to encode frame to JPEG.")

        content_file = ContentFile(buffer.tobytes())
        thumbnail_filename = self.fs.save(thumbnail_name, content_file)

        thumbnail_path = self.fs.path(thumbnail_filename) if hasattr(self.fs, 'path') else thumbnail_filename
        
        return thumbnail_filename, thumbnail_path