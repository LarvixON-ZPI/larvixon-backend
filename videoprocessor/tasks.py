import os
from analysis.models import Substance, VideoAnalysis
from .mock_ml_predict import mock_ml_predict

def get_sorted_predictions(scores):
    """
    Helper function to get all predictions sorted by confidence score.
    """
    if not scores:
        return []

    sorted_predictions = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    
    return sorted_predictions

def process_video_task(analysis_id: int):
    """
    Uses a mock ML model that takes a full video and updates the database.
    """
    try:
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        video_path = analysis.video_file_path
        
        analysis.status = "processing"
        analysis.save()

        print(f"Processing video at {video_path} for analysis ID {analysis_id}")
        mock_results_with_confidence = mock_ml_predict(video_path)
        
        if not mock_results_with_confidence:
            analysis.status = "failed"
        else:
            for substance_name, score in get_sorted_predictions(mock_results_with_confidence):
                detected_substance = Substance.objects.get(name_en=substance_name)
                analysis.analysis_results.create(
                    substance=detected_substance,
                    confidence_score=score
                )
            analysis.status = "completed"
            
        analysis.save()

        os.remove(video_path)
        
    except VideoAnalysis.DoesNotExist:
        print(f"VideoAnalysis with ID {analysis_id} not found.")
        
    except Exception as e:
        if 'analysis' in locals():
            analysis.status = "failed"
            analysis.save()
        print(f"An error occurred: {e}")