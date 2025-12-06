import logging
from typing import Optional
from analysis.models import VideoAnalysis

logger: logging.Logger = logging.getLogger(__name__)


class AnalysisService:
    @staticmethod
    def get_user_analysis(pk: int, user) -> Optional[VideoAnalysis]:
        try:
            return VideoAnalysis.objects.get(pk=pk, user=user)
        except VideoAnalysis.DoesNotExist:
            logger.info(f"Analysis {pk} not found for user {user.id}")
            return None
