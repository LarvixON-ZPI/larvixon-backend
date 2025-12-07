import logging
from datetime import timedelta

from django.utils import timezone

from larvixon_site.settings import VIDEO_LIFETIME_DAYS
from accounts.models import User
from analysis.models import VideoAnalysis
from analysis.errors import (
    AnalysisNotFoundError,
    AnalysisNotFailedError,
    AnalysisTooOldError,
    AnalysisVideoNotFoundError,
)
from patients.services import patient_service
from videoprocessor.tasks import process_video_task

logger: logging.Logger = logging.getLogger(__name__)


class AnalysisService:
    @staticmethod
    def get_user_analysis(pk: int, user) -> VideoAnalysis:
        try:
            return VideoAnalysis.objects.get(pk=pk, user=user)
        except VideoAnalysis.DoesNotExist:
            logger.info(f"Analysis {pk} not found for user {user.id}")
            raise AnalysisNotFoundError()

    @staticmethod
    def get_patients_details_map(analyses: list[VideoAnalysis]) -> dict:
        patient_guids: list[str] = [
            str(analysis.patient_guid) for analysis in analyses if analysis.patient_guid
        ]

        if not patient_guids:
            return {}

        try:
            return patient_service.get_patients_by_guids(patient_guids)
        except Exception:
            logger.error(
                "Failed to fetch patient details for analyses",
                exc_info=True,
            )
            return {}

    @staticmethod
    def get_patient_details_for_analysis(analysis: VideoAnalysis) -> dict:
        if not analysis.patient_guid:
            return {}

        try:
            patient_details = patient_service.get_patient_by_guid(
                str(analysis.patient_guid)
            )
            if patient_details:
                return {str(analysis.patient_guid): patient_details}
            return {}
        except Exception:
            logger.error(
                "Failed to fetch patient details for analysis",
                exc_info=True,
            )
            return {}

    @staticmethod
    def retry_analysis(pk: int, user: User) -> VideoAnalysis:
        analysis: VideoAnalysis = AnalysisService.get_user_analysis(pk, user)

        AnalysisService._validate_analysis_for_retry(analysis)

        AnalysisService._reset_analysis_for_retry(analysis)

        process_video_task.delay(analysis.id)

        return analysis

    @staticmethod
    def _validate_analysis_for_retry(analysis: VideoAnalysis) -> None:
        if analysis.status != VideoAnalysis.Status.FAILED:
            raise AnalysisNotFailedError()

        cutoff_date = timezone.now() - timedelta(days=int(VIDEO_LIFETIME_DAYS))
        if analysis.created_at < cutoff_date:
            raise AnalysisTooOldError(int(VIDEO_LIFETIME_DAYS))

        if not analysis.video:
            raise AnalysisVideoNotFoundError()

    @staticmethod
    def _reset_analysis_for_retry(analysis: VideoAnalysis) -> None:
        analysis.analysis_results.all().delete()
        analysis.status = VideoAnalysis.Status.PENDING
        analysis.error_message = None
        analysis.completed_at = None
        analysis.save()
        logger.info(f"Analysis {analysis.id} reset for retry")
