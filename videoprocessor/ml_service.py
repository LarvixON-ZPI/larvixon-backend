from typing import Dict, Optional
from larvixon_site.settings import MOCK_ML
from .mock_ml_predict import mock_ml_predict
from .send_video_to_ml import send_video_to_ml


def predict_video(video_path: str) -> Optional[Dict[str, float]]:
    if MOCK_ML:
        return mock_ml_predict(video_path)
    return send_video_to_ml(video_path)
