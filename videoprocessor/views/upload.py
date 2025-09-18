from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import FileSystemStorage
from rest_framework.parsers import MultiPartParser, FormParser 
from rest_framework import permissions
from drf_spectacular.utils import extend_schema

class VideoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'video': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        },
    )

    def post(self, request, *args, **kwargs):
        video_file = request.FILES.get('video')

        if not video_file:
            return Response({"error": "No video file provided."}, status=status.HTTP_400_BAD_REQUEST)

        fs = FileSystemStorage()
        
        try:
            filename = fs.save(video_file.name, video_file)
            uploaded_file_url = fs.url(filename)
        except Exception as e:
            return Response({"error": f"Failed to save file: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "Video uploaded and saved successfully.",
            "file_url": uploaded_file_url,
            "filename": filename
        }, status=status.HTTP_201_CREATED)