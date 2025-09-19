import os
from analysis.models import VideoAnalysis
from .mock_ml_predict import mock_ml_predict

def get_top_prediction(scores):
    """
    Helper function to get the top prediction from a dictionary of scores.
    """
    if not scores: 
        return {}

    top_substance = max(scores, key=scores.get)
    
    return {"predicted_substance": top_substance}

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
            analysis.results = get_top_prediction(mock_results_with_confidence)
            analysis.confidence_scores = mock_results_with_confidence
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