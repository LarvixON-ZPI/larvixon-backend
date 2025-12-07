import os
import logging
from celery import shared_task
from django.utils import timezone
from analysis.models import Substance, VideoAnalysis
from django.core.files.storage import default_storage
from tempfile import NamedTemporaryFile

from videoprocessor.services import ml_service

logger = logging.getLogger(__name__)


def get_sorted_predictions(scores):
    """
    Helper function to get all predictions sorted by confidence score.
    """
    if not scores:
        return []
    sorted_predictions = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    return sorted_predictions


@shared_task
def process_video_task(analysis_id: int) -> None:
    """
    Send the video to the ML model for processing. Update the database when done.
    """
    video_path = None

    try:
        analysis = VideoAnalysis.objects.get(id=analysis_id)
    except VideoAnalysis.DoesNotExist:
        logger.error(f"VideoAnalysis with ID {analysis_id} not found.")
        return

    try:
        analysis.status = VideoAnalysis.Status.PENDING
        analysis.error_message = None
        analysis.save()

        with default_storage.open(analysis.video.name, "rb") as f:
            with NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                tmp_file.write(f.read())
                tmp_file.flush()
                video_path = tmp_file.name

                logger.info(
                    f"Processing video at {video_path} for analysis ID {analysis_id}"
                )
                results = ml_service.predict_video(video_path)

        if not results:
            analysis.status = VideoAnalysis.Status.FAILED
            analysis.error_message = (
                "Model request failed: No predictions returned from ML endpoint"
            )
            logger.warning(f"No predictions returned for analysis {analysis_id}")
        else:
            for substance_name, score in get_sorted_predictions(results):
                detected_substance, _ = Substance.objects.get_or_create(
                    name_en=substance_name
                )
                analysis.analysis_results.create(  # type: ignore[attr-defined]
                    substance=detected_substance, confidence_score=score
                )

            analysis.completed_at = timezone.now()
            analysis.status = VideoAnalysis.Status.COMPLETED

        analysis.save()
        logger.info(f"Processing completed for analysis ID {analysis_id}")

    except Exception as e:
        if "analysis" in locals():
            analysis.status = VideoAnalysis.Status.FAILED
            analysis.error_message = f"Model request failed: {str(e)}"
            analysis.save()
        logger.exception(f"An error occurred processing analysis {analysis_id}: {e}")

    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
                logger.debug(f"Cleaned up temp file: {video_path}")
            except Exception as e:
                logger.error(f"Error cleaning up temp file {video_path}: {e}")
