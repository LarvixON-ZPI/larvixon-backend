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
    """Service for processing video analysis tasks."""

    @staticmethod
    def get_sorted_predictions(
        scores: Dict[str, float] | None,
    ) -> List[Tuple[str, float]]:
        """
        Get all predictions sorted by confidence score in descending order.

        Args:
            scores: Dictionary mapping substance names to confidence scores

        Returns:
            List of tuples (substance_name, score) sorted by score descending
        """
        if not scores:
            return []
        return sorted(scores.items(), key=lambda item: item[1], reverse=True)

    @staticmethod
    def save_analysis_results(
        analysis: VideoAnalysis, predictions: Dict[str, float]
    ) -> None:
        """
        Save prediction results to the database.

        Args:
            analysis: VideoAnalysis instance to save results for
            predictions: Dictionary mapping substance names to confidence scores

        Raises:
            Exception: If there's an error saving results to the database
        """
        logger.info(
            f"Saving {len(predictions)} prediction results for analysis {analysis.id}"
        )

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
        """
        Retrieve video analysis by ID.

        Args:
            analysis_id: ID of the video analysis

        Returns:
            VideoAnalysis instance

        Raises:
            VideoAnalysisNotFoundError: If analysis with given ID doesn't exist
        """
        try:
            return VideoAnalysis.objects.get(id=analysis_id)
        except VideoAnalysis.DoesNotExist:
            logger.error(f"VideoAnalysis with ID {analysis_id} not found")
            raise VideoAnalysisNotFoundError(analysis_id)

    @staticmethod
    def process_video(analysis_id: int) -> None:
        """
        Process a video analysis by sending it to the ML model.

        This method:
        1. Retrieves the analysis record
        2. Creates a temporary file from the stored video
        3. Sends it to the ML service for prediction
        4. Saves the results to the database
        5. Updates the analysis status

        Args:
            analysis_id: ID of the video analysis to process

        Raises:
            VideoAnalysisNotFoundError: If analysis doesn't exist
            VideoFileAccessError: If there's an error accessing the video file
            MLPredictionError: If ML prediction fails or returns no results
        """
        logger.info(f"Starting video processing for analysis ID {analysis_id}")
        video_path = None

        try:
            # Get the analysis record
            analysis = VideoProcessingService.get_analysis(analysis_id)

            # Update status to pending
            analysis.status = VideoAnalysis.Status.PENDING
            analysis.error_message = None
            analysis.save()
            logger.debug(f"Set analysis {analysis_id} status to PENDING")

            # Create temporary file for ML processing
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

            # Send to ML service for prediction
            logger.info(f"Sending video to ML service for analysis {analysis_id}")
            try:
                results = ml_service.predict_video(video_path)
            except Exception as e:
                logger.error(f"ML prediction failed for analysis {analysis_id}: {e}")
                raise MLPredictionError(f"ML service error: {str(e)}")

            # Validate results
            if not results:
                logger.warning(f"No predictions returned for analysis {analysis_id}")
                raise MLPredictionError("No predictions returned from ML endpoint")

            # Save results to database
            VideoProcessingService.save_analysis_results(analysis, results)

            # Update analysis as completed
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
