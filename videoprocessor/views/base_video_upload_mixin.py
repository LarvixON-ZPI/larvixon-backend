import os
from rest_framework.response import Response
from rest_framework import status
from analysis.models import VideoAnalysis
from videoprocessor.services import VideoFileManager
from videoprocessor.tasks import process_video_task
from django.db import transaction

MAX_GIGABYTES = 3
MAX_FILE_SIZE = MAX_GIGABYTES * 1024**3


class BaseVideoUploadMixin:
    _video_manager = VideoFileManager()

    def validate_file_size(self, file_size):
        if file_size > MAX_FILE_SIZE:
            file_gb = file_size / 1024**3
            return Response(
                {
                    "error": f"Video file is too large ({file_gb:.2f} GB). Maximum allowed size is {MAX_GIGABYTES} GB."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def save_video_file(self, request, file, title):
        title = (title or "Untitled").strip()
        thumbnail_filename, thumbnail_content = (
            self._video_manager.extract_and_save_first_frame(file)
        )

        video_file_name = os.path.basename(file.name)
        thumbnail_filename = os.path.basename(thumbnail_filename)

        try:
            with transaction.atomic():
                analysis = VideoAnalysis.objects.create(user=request.user, title=title)
                analysis.video.save(video_file_name, file, save=True)
                analysis.thumbnail.save(
                    thumbnail_filename, thumbnail_content, save=True
                )

                if hasattr(request.user, "unmark_new_user"):
                    request.user.unmark_new_user()

        except Exception as e:
            print(f"Error saving video: {e}")
            return Response(
                {"error": f"Failed to process upload: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        process_video_task.delay(analysis.id)  # type: ignore

        return Response(
            {
                "message": "Video processed and analysis started.",
                "analysis_id": analysis.id,
            },
            status=status.HTTP_201_CREATED,
        )
