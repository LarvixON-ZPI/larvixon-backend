from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from django.utils import timezone
from datetime import timedelta
from typing import Optional
from analysis.models import VideoAnalysis
from larvixon_site.settings import VIDEO_LIFETIME_DAYS
from videoprocessor.tasks import process_video_task
from drf_spectacular.utils import extend_schema, OpenApiResponse


def validate_analysis_status(analysis: VideoAnalysis) -> Optional[Response]:
    if analysis.status != VideoAnalysis.Status.FAILED:
        return Response(
            {"error": "Only failed analyses can be retried."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def validate_analysis_age(analysis: VideoAnalysis) -> Optional[Response]:
    cutoff_date = timezone.now() - timedelta(days=int(VIDEO_LIFETIME_DAYS))
    if analysis.created_at < cutoff_date:
        return Response(
            {
                "error": f"Analysis is too old to retry. Only analyses created within the last {VIDEO_LIFETIME_DAYS} days can be retried."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def validate_video_exists(analysis: VideoAnalysis) -> Optional[Response]:
    if not analysis.video:
        return Response(
            {"error": "Video file no longer exists. Cannot retry this analysis."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def reset_analysis_for_retry(analysis: VideoAnalysis) -> None:
    analysis.analysis_results.all().delete()
    analysis.status = VideoAnalysis.Status.PENDING
    analysis.error_message = None
    analysis.completed_at = None
    analysis.save()


class VideoAnalysisRetryView(APIView):
    permission_classes = [IsAuthenticated]

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
            analysis = VideoAnalysis.objects.get(id=pk, user=request.user)  # type: ignore[misc]
        except VideoAnalysis.DoesNotExist:
            return Response(
                {
                    "error": "Analysis not found or you do not have permission to access it."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        validations = [
            validate_analysis_status,
            validate_analysis_age,
            validate_video_exists,
        ]

        for validation in validations:
            error_response = validation(analysis)
            if error_response:
                return error_response

        reset_analysis_for_retry(analysis)
        process_video_task.delay(analysis.id)

        return Response(
            {
                "message": "Analysis retry initiated successfully.",
                "analysis_id": analysis.id,
            },
            status=status.HTTP_200_OK,
        )
