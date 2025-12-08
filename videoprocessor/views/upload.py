import logging

from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from patients.errors import (
    PatientInvalidUUIDError,
    PatientNotFoundError,
    PatientServiceUnavailableError,
    PatientServiceResponseError,
)
from videoprocessor.serializers import VideoUploadSerializer
from videoprocessor.services import VideoUploadService
from videoprocessor.errors import VideoForUploadTooLargeError, VideoWrongFormatError

logger: logging.Logger = logging.getLogger(__name__)


class VideoUploadView(APIView):
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
                    "patient_guid": {
                        "type": "string",
                        "format": "uuid",
                        "description": "GUID of the patient from Patient Service",
                    },
                },
            }
        },
    )
    def post(self, request, *args, **kwargs):
        video_file = request.FILES.get("video")
        description = request.data.get("description", "")
        patient_guid = request.data.get("patient_guid")

        if not video_file:
            return Response(
                {"error": "No video file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            analysis = VideoUploadService.upload_video(
                video_file=video_file,
                description=description,
                patient_guid=patient_guid,
                user=request.user,
            )

            return Response(
                {
                    "message": "Video processed and analysis started.",
                    "analysis_id": analysis.id,
                },
                status=status.HTTP_201_CREATED,
            )
        except PatientInvalidUUIDError:
            logger.warning(f"Invalid Patient GUID format provided: {patient_guid}")
            return Response(
                {"error": "Invalid Patient GUID format."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except PatientNotFoundError:
            logger.warning(f"Patient with GUID {patient_guid} not found.")
            return Response(
                {"error": f"Patient with GUID {patient_guid} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PatientServiceUnavailableError as e:
            logger.error(f"Patient service unavailable for GUID {patient_guid}: {e}")
            return Response(
                {
                    "error": "Patient service is currently unavailable. Please try again later."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except PatientServiceResponseError as e:
            logger.error(f"Patient service response error for GUID {patient_guid}: {e}")
            return Response(
                {"error": f"Error processing patient data: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except VideoForUploadTooLargeError as e:
            logger.warning(f"File size validation failed: {e}")
            return Response(
                {
                    "error": f"Video file is too large ({e.file_size} GB). Maximum allowed size is {e.max_size} GB."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except VideoWrongFormatError as e:
            logger.warning(f"File format validation failed: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Unexpected error during video upload: {e}")
            return Response(
                {"error": "An unexpected error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
