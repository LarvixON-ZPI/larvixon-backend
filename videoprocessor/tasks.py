import logging
from celery import shared_task
from analysis.models import VideoAnalysis

from videoprocessor.services.video_processing_service import VideoProcessingService
from videoprocessor.errors import (
    VideoAnalysisNotFoundError,
    MLPredictionError,
    VideoFileAccessError,
    VideoProcessingError,
)

logger = logging.getLogger(__name__)


@shared_task
def process_video_task(analysis_id: int) -> None:
    logger.info(f"Celery task started for analysis ID {analysis_id}")
    analysis = None

    try:
        VideoProcessingService.process_video(analysis_id)

    except VideoAnalysisNotFoundError as e:
        logger.error(f"Analysis not found: {e}")
        return

    except (MLPredictionError, VideoFileAccessError, VideoProcessingError) as e:
        logger.error(f"Video processing error for analysis {analysis_id}: {e}")
        try:
            analysis = VideoAnalysis.objects.get(id=analysis_id)
            analysis.status = VideoAnalysis.Status.FAILED
            analysis.error_message = f"Processing failed: {str(e)}"
            analysis.save()
            logger.info(f"Updated analysis {analysis_id} status to FAILED")
        except VideoAnalysis.DoesNotExist:
            logger.error(f"Could not update status - analysis {analysis_id} not found")
        except Exception as update_error:
            logger.exception(
                f"Error updating analysis {analysis_id} status: {update_error}"
            )

    except Exception as e:
        logger.exception(f"Unexpected error processing analysis {analysis_id}: {e}")
        try:
            analysis = VideoAnalysis.objects.get(id=analysis_id)
            analysis.status = VideoAnalysis.Status.FAILED
            analysis.error_message = f"Unexpected error: {str(e)}"
            analysis.save()
            logger.info(f"Updated analysis {analysis_id} status to FAILED")
        except Exception as update_error:
            logger.exception(
                f"Error updating analysis {analysis_id} after unexpected error: {update_error}"
            )

    logger.info(f"Celery task completed for analysis ID {analysis_id}")
