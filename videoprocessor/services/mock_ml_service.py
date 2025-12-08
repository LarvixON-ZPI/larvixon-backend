import random

from videoprocessor.services.base_ml_service import BaseMLService

MOCK_SUBSTANCES: list[str] = [
    "cocaine",
    "morphine",
    "ethanol",
    "ketamine",
    "tetrodotoxin",
]

SIMULATE_NONE_FOUND = False


class MockMLService(BaseMLService):
    @staticmethod
    def predict_video(video_path: str) -> dict[str, float] | None:
        if SIMULATE_NONE_FOUND:
            return {}

        if not video_path:
            return {}

        if len(MOCK_SUBSTANCES) < 1:
            return {}

        mock_predicted_substance: str = random.choice(MOCK_SUBSTANCES)

        confidence: float = random.uniform(70.0, 95.0)

        mock_confidences: dict[str, float] = {mock_predicted_substance: confidence}

        mock_confidences.update(
            MockMLService._generate_other_confidences(
                confidence, mock_predicted_substance
            )
        )

        return mock_confidences

    @staticmethod
    def _generate_other_confidences(
        confidence: float, mock_predicted_substance: str
    ) -> dict[str, float]:
        mock_confidences: dict[str, float] = {}
        values: list[float] = [
            random.uniform(0, 1) for _ in range(len(MOCK_SUBSTANCES) - 1)
        ]
        total: float = sum(values)

        remaining_confidence: float = 100.0 - confidence

        other_classes: list[str] = [
            c for c in MOCK_SUBSTANCES if c != mock_predicted_substance
        ]
        for i, substance in enumerate(other_classes):
            mock_confidences[substance] = values[i] / total * remaining_confidence
        return mock_confidences


if __name__ == "__main__":
    print(MockMLService.predict_video("path/to/video.mp4"))
