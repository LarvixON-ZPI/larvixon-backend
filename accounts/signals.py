from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler to create a UserProfile for new users.
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)
