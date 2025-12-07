import logging
from typing import Dict
from larvixon_site.settings import MOCK_ML
from .mock_ml_predict import mock_ml_predict
from .send_video_to_ml import send_video_to_ml

logger = logging.getLogger(__name__)


def predict_video(video_path: str) -> Dict[str, float] | None:
    """
    Predict substance from video using ML service.

    Args:
        video_path: Path to the video file

    Returns:
        Dictionary of predictions with confidence scores, or None if failed
    """
    logger.info(f"Predicting video: {video_path}, MOCK_ML={MOCK_ML}")
    if MOCK_ML:
        return mock_ml_predict(video_path)
    return send_video_to_ml(video_path)
