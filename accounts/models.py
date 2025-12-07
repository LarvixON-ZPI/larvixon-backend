from __future__ import annotations
from typing import TYPE_CHECKING
import warnings
import logging
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import UserManager
from phonenumber_field.modelfields import PhoneNumberField
import os

from accounts.utils import user_picture_upload_to

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any, Dict, List, Tuple


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    This allows for future extensions of user functionality.
    """

    email: models.EmailField = models.EmailField(unique=True)
    first_name: models.CharField = models.CharField(max_length=150, blank=True)
    last_name: models.CharField = models.CharField(max_length=150, blank=True)
    date_joined: models.DateTimeField = models.DateTimeField(default=timezone.now)
    is_active: models.BooleanField = models.BooleanField(default=True)
    is_new_user: models.BooleanField = models.BooleanField(default=True)

    # Use email as the unique identifier for authentication
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "accounts_user"

    def __str__(self) -> str:
        return self.email

    def unmark_new_user(self) -> bool:
        """
        Marks the user as an existing user by setting is_new_user to False.
        Saves the change to the database efficiently.
        Returns True if the status was changed, False otherwise.
        """
        if self.is_new_user:
            self.is_new_user = False
            self.save(update_fields=["is_new_user"])
            return True
        return False


class UserProfile(models.Model):
    """
    Extended profile information for users.
    """

    user: models.OneToOneField[User, User] = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    profile_picture: models.ImageField = models.ImageField(
        upload_to=user_picture_upload_to, blank=True, null=True
    )
    bio: models.TextField = models.TextField(max_length=500, blank=True)
    phone_number: models.CharField = PhoneNumberField(blank=True)
    organization: models.CharField = models.CharField(max_length=255, blank=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.email} - Profile"

    def save(self, *args, **kwargs) -> None:
        try:
            if self.pk:
                old_profile: UserProfile = UserProfile.objects.get(pk=self.pk)
                if (
                    old_profile.profile_picture
                    and old_profile.profile_picture != self.profile_picture
                ):
                    old_profile.profile_picture.delete(save=False)
                    logger.info(f"Old profile picture deleted for user {self.user.id}")
        except UserProfile.DoesNotExist:
            pass

        super(UserProfile, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:
        if self.profile_picture:
            self.profile_picture.delete(save=False)
        return super().delete(*args, **kwargs)
