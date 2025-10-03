import threading
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import FileSystemStorage
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import permissions
from drf_spectacular.utils import extend_schema
from analysis.models import VideoAnalysis
from ..tasks import process_video_task
from rest_framework.request import Request


class VideoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"video": {"type": "string", "format": "binary"}},
            }
        },
    )
    def post(self, request: Request, *args, **kwargs):
        video_file = request.FILES.get("video")
        title = request.data.get("title")
        if(title is None) or (title.strip() == ""):
            title = "Untitled"

        if not video_file:
            return Response(
                {"error": "No video file provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        fs = FileSystemStorage()

        try:
            filename = fs.save(video_file.name, video_file)
            analysis = VideoAnalysis.objects.create(
                user=request.user,
                title=title,
                video_name=filename,
                video_file_path=fs.path(filename),
                status="pending",
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to save file: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        threading.Thread(target=process_video_task, args=(analysis.id,)).start()

        return Response(
            {
                "message": "Video uploaded and saved successfully and analysis created.",
                "filename": filename,
                "file_path": analysis.video_file_path,
                "analysis_id": analysis.id,
            },
            status=status.HTTP_201_CREATED,
        )
