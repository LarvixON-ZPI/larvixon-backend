import os
from analysis.models import Substance, VideoAnalysis
from videoprocessor.mock_ml_predict import mock_ml_predict
from .send_video_to_ml import send_video_to_ml
from django.core.files.storage import default_storage
from tempfile import NamedTemporaryFile


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
        analysis.status = VideoAnalysis.Status.PENDING
        analysis.save()

        with default_storage.open(analysis.video.name, "rb") as f:
            with NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                tmp_file.write(f.read())
                tmp_file.flush()
                video_path = tmp_file.name

                print(f"Processing video at {video_path} for analysis ID {analysis_id}")
                results = send_video_to_ml(video_path)

        if not results:
            analysis.status = VideoAnalysis.Status.FAILED
        else:
            for substance_name, score in get_sorted_predictions(results):
                detected_substance, _ = Substance.objects.get_or_create(
                    name_en=substance_name
                )
                analysis.analysis_results.create(  # type: ignore
                    substance=detected_substance, confidence_score=score
                )
            analysis.status = VideoAnalysis.Status.COMPLETED

        analysis.save()

    except VideoAnalysis.DoesNotExist:
        print(f"VideoAnalysis with ID {analysis_id} not found.")

    except Exception as e:
        if "analysis" in locals():
            analysis.status = VideoAnalysis.Status.FAILED
            analysis.save()
        print(f"An error occurred: {e}")
