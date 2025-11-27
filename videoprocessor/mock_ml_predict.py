import random
from typing import Optional

MOCK_SUBSTANCES: list[str] = [
    "cocaine",
    "morphine",
    "ethanol",
    "ketamine",
    "tetrodotoxin",
]

SIMULATE_NONE_FOUND = False


def mock_ml_predict(video_path: str) -> Optional[dict[str, float]]:
    """
    Returns dictionary of {substance_name: confidence}
    """
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
        _generate_other_confidences(confidence, mock_predicted_substance)
    )

    return mock_confidences


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
    print(mock_ml_predict("path/to/video.mp4"))
