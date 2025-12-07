import logging
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from allauth.mfa.utils import is_mfa_enabled

from accounts.models import User
from accounts.errors import (
    MFARequiredError,
    InvalidMFACodeError,
    InvalidTokenError,
    MissingRefreshTokenError,
)
from accounts.services.mfa import MFAService

logger: logging.Logger = logging.getLogger(__name__)


class AuthenticationService:
    @staticmethod
    def register_user(validated_data: dict) -> tuple[User, dict]:
        from accounts.serializers import UserRegistrationSerializer

        serializer = UserRegistrationSerializer(data=validated_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh: RefreshToken = RefreshToken.for_user(user)
        tokens: dict[str, str] = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        logger.info(f"User {user.id} registered successfully")
        return user, tokens

    @staticmethod
    def login_user(
        email: str, password: str, mfa_code: str | None = None
    ) -> tuple[User, dict]:
        from accounts.serializers import UserLoginSerializer

        serializer = UserLoginSerializer(data={"email": email, "password": password})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        if is_mfa_enabled(user):
            if not mfa_code:
                logger.info(f"MFA required for user {user.id}")
                raise MFARequiredError()

            is_valid, verification_status, _ = MFAService.verify_mfa_code(
                user, mfa_code
            )
            if not is_valid:
                logger.warning(
                    f"Invalid MFA code for user {user.id}: {verification_status.value}"
                )
                raise InvalidMFACodeError(verification_status.value)

        refresh: RefreshToken = RefreshToken.for_user(user)
        tokens: dict[str, str] = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        logger.info(f"User {user.id} logged in successfully")
        return user, tokens

    @staticmethod
    def logout_user(refresh_token: str) -> None:
        if not refresh_token:
            raise MissingRefreshTokenError()

        try:
            token = RefreshToken(refresh_token)  # type: ignore
            token.blacklist()
            logger.info("User logged out successfully")
        except TokenError as e:
            logger.error(f"Token error during logout: {e}")
            raise InvalidTokenError(str(e))

    @staticmethod
    def social_login(user: User, mfa_code: str | None = None) -> dict[str, str]:
        if is_mfa_enabled(user):
            if not mfa_code:
                logger.info(f"MFA required for social login user {user.pk}")
                raise MFARequiredError()

            is_valid, verification_status, _ = MFAService.verify_mfa_code(
                user, mfa_code
            )
            if not is_valid:
                logger.warning(
                    f"Invalid MFA code for social login user {user.pk}: {verification_status.value}"
                )
                raise InvalidMFACodeError(verification_status.value)

        refresh: RefreshToken = RefreshToken.for_user(user)
        tokens: dict[str, str] = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        logger.info(f"User {user.pk} logged in via social provider successfully")
        return tokens
