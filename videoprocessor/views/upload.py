import os
import threading
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework import serializers
from django.db import transaction
from drf_spectacular.utils import extend_schema

from analysis.models import VideoAnalysis
from ..tasks import process_video_task
from ..video_file_manager import VideoFileManager


class VideoUploadSerializer(serializers.Serializer):
    """
    empty serializer for video upload view to supress warnings
    """

    pass


class VideoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VideoUploadSerializer

    _video_manager = VideoFileManager()

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "video": {"type": "string", "format": "binary"},
                    "title": {"type": "string"},
                },
            }
        },
    )
    def post(self, request: Request, *args, **kwargs):
        video_file = request.FILES.get("video")
        title = request.data.get("title")

        if not video_file:
            return Response(
                {"error": "No video file provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        title = title.strip() if title else "Untitled"
        thumbnail_filename, thumbnail_content = (
            self._video_manager.extract_and_save_first_frame(video_file)
        )

        video_file_name = os.path.basename(video_file.name)
        thumbnail_filename = os.path.basename(thumbnail_filename)

        try:
            with transaction.atomic():
                analysis = VideoAnalysis.objects.create(user=request.user, title=title)
                analysis.video.save(video_file_name, video_file, save=True)
                analysis.thumbnail.save(
                    thumbnail_filename, thumbnail_content, save=True
                )

                request.user.unmark_new_user()  # type: ignore

        except (IOError, Exception) as e:
            print(e)
            return Response(
                {"error": f"Failed to process upload or save record: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        threading.Thread(target=process_video_task, args=(analysis.id,)).start()

        return Response(
            {
                "message": "Video uploaded, thumbnail created, and analysis initiated.",
                "analysis_id": analysis.id,
            },
            status=status.HTTP_201_CREATED,
        )
