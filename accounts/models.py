from __future__ import annotations
from typing import TYPE_CHECKING
from warnings import deprecated
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import UserManager
from phonenumber_field.modelfields import PhoneNumberField
import os

from accounts.utils import user_picture_upload_to

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any, Dict, Optional, List, Tuple


@deprecated("Use {user_picture_upload_to} instead")
def user_profile_picture_path(instance, filename):
    return f"profile_pics/user_{instance.user.id}/{filename}"


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

    @property
    def get_profile_picture_url(self):
        """Returns the URL of the profile picture if it exists."""
        if self.profile_picture:
            return self.profile_picture.url

    def save(self, *args, **kwargs):
        try:
            this = UserProfile.objects.get(id=self.id)
            if this.profile_picture != self.profile_picture:
                if this.profile_picture and os.path.exists(this.profile_picture.path):
                    this.profile_picture.delete(save=False)
        except UserProfile.DoesNotExist:
            pass

        super(UserProfile, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.profile_picture:
            self.profile_picture.delete(save=False)
        super(UserProfile, self).delete(*args, **kwargs)
