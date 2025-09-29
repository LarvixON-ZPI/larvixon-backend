from typing import List, Tuple
from django.db import models
from accounts.models import User


class VideoAnalysis(models.Model):
    """
    Model to track user's video analysis history.
    """

    STATUS_CHOICES: List[Tuple[str, str]] = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id: models.BigAutoField = models.BigAutoField(primary_key=True)

    user: models.ForeignKey[User, User] = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="analyses"
    )
    title: models.CharField = models.CharField(max_length=255, blank=True)
    video_name: models.CharField = models.CharField(max_length=255)
    video_file_path: models.CharField = models.CharField(max_length=500)
    status: models.CharField = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    completed_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    # Results
    results: models.JSONField = models.JSONField(
        null=True, blank=True
    )  # Store analysis results
    confidence_scores: models.JSONField = models.JSONField(
        null=True, blank=True
    )  # Store confidence scores

    # User feedback for model improvement
    actual_substance: models.CharField = models.CharField(
        max_length=100, blank=True, null=True
    )
    user_feedback: models.TextField = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.video_name} ({self.status})"
