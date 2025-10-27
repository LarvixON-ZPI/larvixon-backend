import os
from typing import List, Tuple
import uuid
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
    title: models.CharField = models.CharField(
        max_length=255, default="Untitled"
    )  # consider making this field unique for the user?

    user: models.ForeignKey[User, User] = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="analyses"
    )
    video = models.FileField(upload_to=user_video_upload_to)
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
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    completed_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    actual_substance: models.CharField = models.CharField(
        max_length=100, blank=True, null=True
    )
    user_feedback: models.TextField = models.TextField(blank=True)

    def delete(self, *args, **kwargs):
        if self.video:
            self.video.delete(save=False)
        if self.thumbnail:
            self.thumbnail.delete(save=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} - {self.video_name} ({self.status})"


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
        return f"{self.analysis.title} - {self.substance.name_en} ({self.confidence_score})"
