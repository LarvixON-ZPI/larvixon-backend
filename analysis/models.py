from django.core.validators import FileExtensionValidator
from typing import TYPE_CHECKING, Any
from django.db import models
from accounts.models import User
from accounts.utils import user_thumbnail_upload_to, user_video_upload_to


class VideoAnalysis(models.Model):
    """
    Model to track user's video analysis history.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    description: models.TextField = models.TextField(blank=True, default="")

    user: models.ForeignKey[User, User] = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="analyses"
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analyses",
    )
    video = models.FileField(
        upload_to=user_video_upload_to,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["mp4"])],
    )
    thumbnail = models.ImageField(
        upload_to=user_thumbnail_upload_to,
        blank=True,
        null=True,
    )
    status: models.CharField = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error_message: models.TextField = models.TextField(
        blank=True, null=True, help_text="Error details when analysis fails"
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    completed_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    actual_substance: models.CharField = models.CharField(
        max_length=100, blank=True, null=True
    )
    user_feedback: models.TextField = models.TextField(blank=True)

    if TYPE_CHECKING:
        analysis_results: Any

    def delete(self, *args, **kwargs):
        if self.video and self.video.name:
            self.video.delete(save=False)
        if self.thumbnail and self.thumbnail.name:
            self.thumbnail.delete(save=False)

        return super().delete(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.description} - {self.video.name} ({self.status})"


class Substance(models.Model):
    """
    Model to represent substances that can be detected in videos.
    """

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    name_en: models.CharField = models.CharField(max_length=100, unique=True)
    name_pl: models.CharField = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )

    def __str__(self) -> str:
        return self.name_en


class AnalysisResult(models.Model):
    """
    Model to store detailed results of each analysis.
    """

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    analysis: models.ForeignKey[VideoAnalysis, VideoAnalysis] = models.ForeignKey(
        VideoAnalysis, on_delete=models.CASCADE, related_name="analysis_results"
    )
    substance: models.ForeignKey[Substance, Substance] = models.ForeignKey(
        Substance, on_delete=models.PROTECT, related_name="detection_results"
    )
    confidence_score: models.FloatField = models.FloatField()
    detected_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("analysis", "substance")

    def __str__(self) -> str:
        return f"{self.analysis.description} - {self.substance.name_en} ({self.confidence_score})"
