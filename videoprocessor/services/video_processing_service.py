import os
import logging
from typing import Dict, List, Tuple
from django.utils import timezone
from django.core.files.storage import default_storage
from tempfile import NamedTemporaryFile

from analysis.models import Substance, VideoAnalysis
from videoprocessor.services.ml_service import ml_service
from videoprocessor.errors import (
    VideoAnalysisNotFoundError,
    MLPredictionError,
    VideoFileAccessError,
)

logger = logging.getLogger(__name__)


class VideoProcessingService:
    @staticmethod
    def get_sorted_predictions(
        scores: Dict[str, float] | None,
    ) -> List[Tuple[str, float]]:
        if not scores:
            return []
        return sorted(scores.items(), key=lambda item: item[1], reverse=True)

    @staticmethod
    def save_analysis_results(
        analysis: VideoAnalysis, predictions: Dict[str, float]
    ) -> None:
        if not predictions:
            logger.info(f"No predictions to save for analysis {analysis.id}")
            return

        logger.info(
            f"Saving {len(predictions)} prediction results for analysis {analysis.id}"
        )

        try:
            VideoAnalysis.objects.get(id=analysis.id)
        except VideoAnalysis.DoesNotExist:
            logger.error(
                f"Analysis {analysis.id} was deleted before results could be saved"
            )
            raise VideoAnalysisNotFoundError(analysis.id)

        for substance_name, score in VideoProcessingService.get_sorted_predictions(
            predictions
        ):
            detected_substance, created = Substance.objects.get_or_create(
                name_en=substance_name
            )
            if created:
                logger.debug(f"Created new substance: {substance_name}")

            analysis.analysis_results.create(  # type: ignore[attr-defined]
                substance=detected_substance, confidence_score=score
            )

        logger.info(f"Successfully saved results for analysis {analysis.id}")

    @staticmethod
    def get_analysis(analysis_id: int) -> VideoAnalysis:
        try:
            return VideoAnalysis.objects.get(id=analysis_id)
        except VideoAnalysis.DoesNotExist:
            logger.error(f"VideoAnalysis with ID {analysis_id} not found")
            raise VideoAnalysisNotFoundError(analysis_id)

    @staticmethod
    def process_video(analysis_id: int) -> None:
        logger.info(f"Starting video processing for analysis ID {analysis_id}")
        video_path = None

        try:
            analysis = VideoProcessingService.get_analysis(analysis_id)

            analysis.status = VideoAnalysis.Status.PENDING
            analysis.error_message = None
            analysis.save()
            logger.debug(f"Set analysis {analysis_id} status to PENDING")

            try:
                with default_storage.open(analysis.video.name, "rb") as f:
                    with NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                        tmp_file.write(f.read())
                        tmp_file.flush()
                        video_path = tmp_file.name
                        logger.debug(f"Created temporary file at {video_path}")
            except Exception as e:
                logger.error(
                    f"Error accessing video file for analysis {analysis_id}: {e}"
                )
                raise VideoFileAccessError(f"Failed to access video file: {str(e)}")

            logger.info(f"Sending video to ML service for analysis {analysis_id}")
            try:
                results = ml_service.predict_video(video_path)
            except Exception as e:
                logger.error(f"ML prediction failed for analysis {analysis_id}: {e}")
                raise MLPredictionError(f"ML service error: {str(e)}")

            if results is None:
                logger.warning(f"No predictions returned for analysis {analysis_id}")
                raise MLPredictionError("No predictions returned from ML endpoint")

            VideoProcessingService.save_analysis_results(analysis, results)

            analysis.completed_at = timezone.now()
            analysis.status = VideoAnalysis.Status.COMPLETED
            analysis.save()

            logger.info(f"Successfully completed processing for analysis {analysis_id}")

        finally:
            # Clean up temporary file
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    logger.debug(f"Cleaned up temporary file: {video_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up temp file {video_path}: {e}")
