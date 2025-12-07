import logging
from larvixon_site.settings import MOCK_ML
from .base_ml_service import BaseMLService
from .mock_ml_predict import MockMLService
from .send_video_to_ml import APIMLService

logger: logging.Logger = logging.getLogger(__name__)


def get_ml_service() -> BaseMLService:
    if MOCK_ML:
        return MockMLService()
    return APIMLService()


ml_service: BaseMLService = get_ml_service()
