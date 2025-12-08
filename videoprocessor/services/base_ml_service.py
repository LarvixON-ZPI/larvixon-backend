from abc import ABC, abstractmethod
from typing import Dict


class BaseMLService(ABC):
    """Abstract base class for ML prediction services."""

    @abstractmethod
    def predict_video(self, video_path: str) -> Dict[str, float] | None:
        """
        Predict substance from video using ML service.

        Args:
            video_path: Path to the video file

        Returns:
            Dictionary of predictions with confidence scores, or None if failed
        """
        pass
