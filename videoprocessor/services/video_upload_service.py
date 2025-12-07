import os
import logging
from django.core.files import File
from django.db import transaction

from analysis.models import VideoAnalysis
from larvixon_site import settings
from patients.errors import (
    PatientNotFoundError,
)
from videoprocessor.errors import (
    VideoForUploadTooLargeError,
    VideoNoFileError,
    VideoWrongFormatError,
)
from videoprocessor.services import VideoFileManager
from patients.services.patients import patient_service

MAX_GIGABYTES = 3
GIGABYTE = 1024**3
MAX_FILE_SIZE: int = MAX_GIGABYTES * GIGABYTE
ALLOWED_EXTENSIONS: list[str] = [".mp4"]

logger: logging.Logger = logging.getLogger(__name__)

UPLOAD_DIR: str = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class VideoUploadService:
    @staticmethod
    def upload_video(video_file, description, patient_guid, user) -> VideoAnalysis:
        if not video_file:
            raise VideoNoFileError()

        if patient_guid:
            patient_service.validate_uuid(patient_guid)

            patient = patient_service.get_patient_by_guid(patient_guid)
            if not patient:
                logger.warning(f"Patient with GUID {patient_guid} not found.")
                raise PatientNotFoundError(
                    f"Patient with GUID {patient_guid} not found."
                )

        try:
            VideoUploadService.validate_file_format(video_file.name)
        except VideoWrongFormatError as e:
            logger.warning(f"File format validation failed: {e}")
            raise

        try:
            VideoUploadService.validate_file_size(video_file.size)
        except VideoForUploadTooLargeError as e:
            logger.warning(f"File size validation failed: {e}")
            raise

        analysis: VideoAnalysis = VideoUploadService.save_and_process_video(
            user=user,
            video_file=video_file,
            description=description,
            patient_guid=patient_guid,
        )

        return analysis

    @staticmethod
    def validate_file_size(file_size: int) -> None:
        if file_size > MAX_FILE_SIZE:
            file_gb = int(file_size / GIGABYTE)
            raise VideoForUploadTooLargeError(file_size=file_gb, max_size=MAX_GIGABYTES)

    @staticmethod
    def validate_file_format(filename: str) -> None:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise VideoWrongFormatError(
                f"Unsupported file format: {ext}. Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed."
            )

    @staticmethod
    def save_and_process_video(
        user,
        video_file,
        description: str = "",
        patient_guid: str | None = None,
    ) -> VideoAnalysis:
        logger.info(f"Saving video for user {user.id}")

        thumbnail_filename, thumbnail_content = (
            VideoFileManager.extract_and_save_first_frame(video_file)
        )

        video_file_name = video_file.name
        thumbnail_filename = os.path.basename(thumbnail_filename)

        with transaction.atomic():
            analysis = VideoAnalysis.objects.create(
                user=user,
                description=description,
                patient_guid=patient_guid,
            )
            analysis.video.save(video_file_name, video_file, save=True)
            analysis.thumbnail.save(thumbnail_filename, thumbnail_content, save=True)

            if hasattr(user, "unmark_new_user"):
                user.unmark_new_user()

        logger.info(f"Video saved successfully, analysis ID: {analysis.id}")

        # Import here to avoid circular import
        from videoprocessor.tasks import process_video_task

        process_video_task.delay(analysis.id)

        return analysis

    @staticmethod
    def _finalize_upload(user, file_path, filename, description, patient_guid) -> None:
        try:
            VideoUploadService.validate_file_format(filename)
        except VideoWrongFormatError as e:
            logger.warning(f"File format validation failed: {e}")
            os.remove(file_path)
            raise
        try:
            with open(file_path, "rb") as f:
                django_file: File[bytes] = File(f, name=filename)
                analysis: VideoAnalysis = VideoUploadService.save_and_process_video(
                    user=user,
                    video_file=django_file,
                    description=description,
                    patient_guid=patient_guid,
                )
            os.remove(file_path)
        except Exception as e:
            logger.exception(f"Error saving video: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
