from rest_framework import serializers
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from videoprocessor.views.base_video_upload_mixin import BaseVideoUploadMixin


class VideoUploadSerializer(serializers.Serializer):
    """
    empty serializer for video upload view to supress warnings
    """

    pass


class VideoUploadView(BaseVideoUploadMixin, APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VideoUploadSerializer

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
    def post(self, request, *args, **kwargs):
        video_file = request.FILES.get("video")
        title = request.data.get("title")

        if not video_file:
            return Response(
                {"error": "No video file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        error = self.validate_file_size(video_file.size)
        if error:
            print(error.data)
            return error

        return self.save_video_file(request, video_file, title)
