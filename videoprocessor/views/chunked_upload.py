import os
from django.conf import settings
from django.core.files import File
from rest_framework import status, permissions
from rest_framework.parsers import BaseParser
from rest_framework.response import Response
from rest_framework.views import APIView

from videoprocessor.views.base_video_upload_mixin import BaseVideoUploadMixin

UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class OctetStreamParser(BaseParser):
    media_type = "application/octet-stream"

    def parse(self, stream, media_type=None, parser_context=None):
        return stream


class ChunkedUploadView(BaseVideoUploadMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [OctetStreamParser]

    def post(self, request, *args, **kwargs):
        upload_id = request.headers.get("Upload-Id")
        filename = request.headers.get("Filename")
        content_range = request.headers.get("Content-Range")
        title = request.headers.get("Title")

        if not upload_id or not filename:
            return Response(
                {"error": "Missing Upload-Id or Filename"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_path = os.path.join(UPLOAD_DIR, f"{upload_id}_{filename}")
        with open(file_path, "ab") as destination:
            for chunk in request.stream:
                destination.write(chunk)

        if content_range and "/" in content_range:
            _, total_size = content_range.split("/")
            total_size = int(total_size)
            error = self.validate_file_size(total_size)
            if error:
                os.remove(file_path)
                return error

            if os.path.getsize(file_path) >= total_size:
                return self._finalize_upload(request, file_path, filename, title)

        return Response({"message": "Chunk uploaded successfully."})

    def _finalize_upload(self, request, file_path, filename, title):
        with open(file_path, "rb") as f:
            django_file = File(f)
            response = self.save_video_file(request, django_file, title)
        os.remove(file_path)
        return response
