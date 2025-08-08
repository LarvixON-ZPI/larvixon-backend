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
        db_table = 'accounts_user'

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
