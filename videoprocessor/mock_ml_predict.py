import random

MOCK_CLASS_NAMES = ["cocaine", "morphine", "ethanol", "ketamine", "morphine", "tetrodotoxin"]

def mock_ml_predict(video_path: str) -> dict:
    """
    Simulates a machine learning model that takes an entire video file as input. 
    (whole video will be pased to the model and splited into frames inside the model in real scenario)
    Returns mock predictions and confidence scores for the video.
    """
    if not video_path:
        return {}

    mock_prediction = random.choice(MOCK_CLASS_NAMES)
    
    confidence = random.uniform(0.7, 0.99)
    
    mock_scores = {cls_name: 0.0 for cls_name in MOCK_CLASS_NAMES}
    mock_scores[mock_prediction] = confidence
    
    # distribute the remaining confidence among other classes
    remaining_confidence = 1.0 - confidence
    other_classes = [c for c in MOCK_CLASS_NAMES if c != mock_prediction]
    if other_classes:
        per_other_class_confidence = remaining_confidence / len(other_classes)
        for cls_name in other_classes:
            mock_scores[cls_name] = per_other_class_confidence
            
    return mock_scores