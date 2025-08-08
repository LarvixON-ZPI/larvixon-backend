from __future__ import annotations
from typing import TYPE_CHECKING
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import UserManager

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any, Dict, Optional, List, Tuple


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    This allows for future extensions of user functionality.
    """
    email: models.EmailField = models.EmailField(unique=True)
    first_name: models.CharField = models.CharField(max_length=150, blank=True)
    last_name: models.CharField = models.CharField(max_length=150, blank=True)
    date_joined: models.DateTimeField = models.DateTimeField(
        default=timezone.now)
    is_active: models.BooleanField = models.BooleanField(default=True)

    # Use email as the unique identifier for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'auth_user'

    def __str__(self) -> str:
        return self.email


class UserProfile(models.Model):
    """
    Extended profile information for users.
    """
    user: models.OneToOneField[User, User] = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    bio: models.TextField = models.TextField(max_length=500, blank=True)
    phone_number: models.CharField = models.CharField(
        max_length=20, blank=True)
    organization: models.CharField = models.CharField(
        max_length=255, blank=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.email} - Profile"


class VideoAnalysis(models.Model):
    """
    Model to track user's video analysis history.
    """
    STATUS_CHOICES: List[Tuple[str, str]] = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id: models.BigAutoField = models.BigAutoField(primary_key=True)

    user: models.ForeignKey[User, User] = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='analyses')
    video_name: models.CharField = models.CharField(max_length=255)
    video_file_path: models.CharField = models.CharField(max_length=500)
    status: models.CharField = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    completed_at: models.DateTimeField = models.DateTimeField(
        null=True, blank=True)

    # Results
    results: models.JSONField = models.JSONField(
        null=True, blank=True)  # Store analysis results
    confidence_scores: models.JSONField = models.JSONField(
        null=True, blank=True)  # Store confidence scores

    # User feedback for model improvement
    actual_substance: models.CharField = models.CharField(
        max_length=100, blank=True, null=True)
    user_feedback: models.TextField = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.user.email} - {self.video_name} ({self.status})"
