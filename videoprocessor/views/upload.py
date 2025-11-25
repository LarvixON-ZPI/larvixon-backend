import os
from rest_framework import serializers
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from patients.models import Patient
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
                    "description": {"type": "string"},
                    "patient_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "UUID of the patient (optional)",
                    },
                },
            }
        },
    )
    def post(self, request, *args, **kwargs):
        video_file = request.FILES.get("video")
        description = request.data.get("description", "")
        patient_id = request.data.get("patient_id")

        if not video_file:
            return Response(
                {"error": "No video file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if patient_id:
            try:
                if not Patient.objects.filter(id=patient_id).exists():
                    return Response(
                        {"error": f"Patient with ID {patient_id} not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            except Exception:
                return Response(
                    {"error": "Invalid Patient ID format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        error = self.validate_file_size(video_file.size)
        if error:
            print(error.data)
            return error

        ext = os.path.splitext(video_file.name)[1].lower()
        if ext != ".mp4":
            return Response(
                {
                    "error": f"Unsupported file format: {ext}. For now only .mp4 files are allowed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self.save_video_file(request, video_file, description, patient_id)
