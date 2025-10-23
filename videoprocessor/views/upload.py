import threading
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import permissions
from rest_framework.request import Request
from django.db import transaction
from drf_spectacular.utils import extend_schema

from analysis.models import VideoAnalysis
from ..tasks import process_video_task
from ..video_file_manager import VideoFileManager

class VideoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    _video_manager = VideoFileManager()

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"video": {"type": "string", "format": "binary"}, "title": {"type": "string"}},
            }
        },
    )
    def post(self, request: Request, *args, **kwargs):
        video_file = request.FILES.get("video")
        title = request.data.get("title")

        if not video_file:
            return Response(
                {"error": "No video file provided."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        title = title.strip() if title else "Untitled"

        try:
            video_filename, video_path = self._video_manager.save_video_file(video_file)

            thumbnail_filename, thumbnail_path = self._video_manager.extract_and_save_first_frame(video_path, video_filename)

            with transaction.atomic():
                analysis = VideoAnalysis.objects.create(
                    user=request.user,
                    title=title,
                    video_name=video_filename,
                    video_file_path=video_path,
                    thumbnail_name=thumbnail_filename,
                    thumbnail_path=thumbnail_path,
                    status="pending",
                )
                
            request.user.unmark_new_user()

        except (IOError, Exception) as e:
            return Response(
                {"error": f"Failed to process upload or save record: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        threading.Thread(target=process_video_task, args=(analysis.id,)).start()

        return Response(
            {
                "message": "Video uploaded, thumbnail created, and analysis initiated.",
                "analysis_id": analysis.id,
                "video_path": video_path,
                "thumbnail_path": thumbnail_path,
            },
            status=status.HTTP_201_CREATED,
        )
