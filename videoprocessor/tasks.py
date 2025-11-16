from datetime import timedelta
import os
from celery import shared_task
from django.utils import timezone
from analysis.models import Substance, VideoAnalysis
from larvixon_site.settings import VIDEO_LIFETIME_DAYS
from .ml_service import predict_video
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


@shared_task
def process_video_task(analysis_id: int):
    """
    Send the video to the ML model for processing. Update the database when done.
    """
    video_path = None

    try:
        analysis = VideoAnalysis.objects.get(id=analysis_id)
    except VideoAnalysis.DoesNotExist:
        print(f"VideoAnalysis with ID {analysis_id} not found.")
        return

    try:
        analysis.status = VideoAnalysis.Status.PENDING
        analysis.save()

        with default_storage.open(analysis.video.name, "rb") as f:
            with NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                tmp_file.write(f.read())
                tmp_file.flush()
                video_path = tmp_file.name

                print(f"Processing video at {video_path} for analysis ID {analysis_id}")
                results = predict_video(video_path)

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

            analysis.completed_at = timezone.now()
            analysis.status = VideoAnalysis.Status.COMPLETED

        analysis.save()
        print(f"Processing completed for analysis ID {analysis_id}")

    except Exception as e:
        if "analysis" in locals():
            analysis.status = VideoAnalysis.Status.FAILED
            analysis.save()
        print(f"An error occurred: {e}")

    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
                print(f"Cleaned up temp file: {video_path}")
            except Exception as e:
                print(f"Error cleaning up temp file {video_path}: {e}")


@shared_task
def cleanup_old_analyses_videos():
    """
    This task runs on a schedule.
    It finds analyses older than 14 days, deletes their associated
    video file (but keeps the thumbnail), and sets the
    database 'video' field to NULL.
    """
    print(
        "CELERY BEAT: Running daily cleanup: Pruning video files older than 14 days..."
    )

    fourteen_days_ago = timezone.now() - timedelta(days=VIDEO_LIFETIME_DAYS)  # type: ignore

    analyses_to_prune = VideoAnalysis.objects.filter(
        created_at__lte=fourteen_days_ago, video__isnull=False
    )

    for analysis in analyses_to_prune:
        try:
            if analysis.video:
                analysis.video.delete(save=False)
        except Exception as e:
            print(f"CELERY BEAT: Error deleting video for analysis {analysis.id}: {e}")

    updated_count = analyses_to_prune.update(video=None)

    if updated_count > 0:
        print(
            f"CELERY BEAT: Successfully pruned video files for {updated_count} analyses."
        )
    else:
        print("CELERY BEAT: No old analyses found for video pruning.")

    return f"Pruned video files for {updated_count} analyses."
