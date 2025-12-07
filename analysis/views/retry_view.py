import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema, OpenApiResponse

from larvixon_site.settings import VIDEO_LIFETIME_DAYS
from accounts.models import User
from analysis.serializers import RetryResponseSerializer
from analysis.services.analysis import AnalysisService
from analysis.errors import (
    AnalysisNotFoundError,
    AnalysisCannotBeRetriedError,
)

logger = logging.getLogger(__name__)


class VideoAnalysisRetryView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RetryResponseSerializer

    @extend_schema(
        summary="Retry failed analysis",
        description=(
            f"Retry a failed video analysis. "
            f"The analysis must have been created within the last {VIDEO_LIFETIME_DAYS} days and still have a video file."
        ),
        responses={
            200: OpenApiResponse(
                description="Analysis retry initiated successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "analysis_id": {"type": "integer"},
                    },
                },
            ),
            400: OpenApiResponse(description="Analysis cannot be retried"),
            404: OpenApiResponse(description="Analysis not found"),
        },
    )
    def post(self, request: Request, pk: int) -> Response:
        """
        Retry a failed analysis by ID.
        """
        try:
            user = request.user
            if not isinstance(user, User):
                raise ValueError("Invalid user in request")
            analysis = AnalysisService.retry_analysis(pk, user)

            return Response(
                {
                    "message": "Analysis retry initiated successfully.",
                    "analysis_id": analysis.id,
                },
                status=status.HTTP_200_OK,
            )
        except AnalysisNotFoundError:
            logger.warning(
                f"Analysis {pk} not found for user {request.user.pk} during retry attempt"
            )
            return Response(
                {
                    "error": "Analysis not found or you do not have permission to access it."
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except AnalysisCannotBeRetriedError as e:
            return Response(
                {"error": e.message},
                status=status.HTTP_400_BAD_REQUEST,
            )
