import logging
from types import SimpleNamespace
from django.db import transaction
from django.db.models.query import QuerySet

from accounts.models import User, UserProfile
from analysis.models import VideoAnalysis

logger: logging.Logger = logging.getLogger(__name__)


class ProfileService:
    @staticmethod
    def get_or_create_profile(user: User) -> UserProfile:
        profile, created = UserProfile.objects.get_or_create(user=user)
        if created:
            logger.info(f"Created profile for user {user.pk}")
        return profile

    @staticmethod
    @transaction.atomic
    def get_user_stats(user: User) -> dict[str, int]:
        analyses: QuerySet[VideoAnalysis, VideoAnalysis] = VideoAnalysis.objects.filter(
            user=user
        )

        stats: dict[str, int] = {
            "total_analyses": analyses.count(),
            "completed_analyses": analyses.filter(status="completed").count(),
            "pending_analyses": analyses.filter(status="pending").count(),
            "processing_analyses": analyses.filter(status="processing").count(),
            "failed_analyses": analyses.filter(status="failed").count(),
        }

        logger.debug(f"Retrieved stats for user {user.pk}: {stats}")
        return stats

    @staticmethod
    def change_password(
        user: User,
        old_password: str | None,
        new_password: str | None,
        confirm_password: str | None,
    ) -> None:
        from accounts.serializers import PasswordChangeSerializer

        serializer = PasswordChangeSerializer(
            data={
                "old_password": old_password,
                "new_password": new_password,
                "confirm_password": confirm_password,
            },
            context={"request": SimpleNamespace(user=user)},
        )
        serializer.is_valid(raise_exception=True)

        user.set_password(new_password)
        user.save()

        logger.info(f"Password changed successfully for user {user.pk}")
