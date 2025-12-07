from enum import Enum
import logging
from allauth.mfa.models import Authenticator
import pyotp

from qrcode.image.pil import PilImage
from qrcode.image.pure import PyPNGImage

from allauth.mfa.utils import is_mfa_enabled

import pyotp
import qrcode
from io import BytesIO
import base64

from accounts.errors import (
    MFAAlreadyEnabledError,
    MFANotEnabledError,
    MFADeviceNotFoundError,
    InvalidMFACodeError,
)
from accounts.models import User

logger: logging.Logger = logging.getLogger(__name__)


class MFAService:
    @staticmethod
    def setup(user: User) -> tuple[Authenticator, str, str]:
        if is_mfa_enabled(user):
            raise MFAAlreadyEnabledError()

        pyotp_instance = pyotp.TOTP(pyotp.random_base32())
        secret = pyotp_instance.secret

        if Authenticator.objects.filter(
            user=user, type=Authenticator.Type.TOTP
        ).exists():
            Authenticator.objects.filter(
                user=user, type=Authenticator.Type.TOTP
            ).delete()

        device: Authenticator = Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.TOTP,
            data={"secret": secret},
        )

        otp_uri: str = pyotp_instance.provisioning_uri(
            name=user.email, issuer_name="Larvixon"
        )

        img: PilImage | PyPNGImage = qrcode.make(otp_uri)
        buf = BytesIO()
        img.save(buf, format="PNG")  # type: ignore[call-arg]
        qr_code_base64: str = base64.b64encode(buf.getvalue()).decode("utf-8")

        return device, secret, qr_code_base64

    class MFAVerificationStatus(Enum):
        SUCCESS = "Success"
        DEVICE_NOT_FOUND = "MFA secret key not found."
        DEVICE_NOT_CONFIRMED = "MFA device is not confirmed."
        INVALID_CODE = "Invalid MFA code"

    @staticmethod
    def verify_mfa_code(
        user, mfa_code, is_confirmed_check=True
    ) -> tuple[bool, MFAVerificationStatus, Authenticator | None]:
        try:
            device = Authenticator.objects.get(user=user, type=Authenticator.Type.TOTP)
        except Authenticator.DoesNotExist:
            logger.warning(f"MFA device not found for user {user.id}")
            return False, MFAService.MFAVerificationStatus.DEVICE_NOT_FOUND, None

        if is_confirmed_check and not device.last_used_at:
            return False, MFAService.MFAVerificationStatus.DEVICE_NOT_CONFIRMED, device

        secret = device.data.get("secret")
        if not secret:
            return False, MFAService.MFAVerificationStatus.DEVICE_NOT_FOUND, device

        totp_instance = pyotp.TOTP(secret)
        if not totp_instance.verify(mfa_code):
            return False, MFAService.MFAVerificationStatus.INVALID_CODE, device
        return True, MFAService.MFAVerificationStatus.SUCCESS, device

    @staticmethod
    def activate_mfa_device(user: User, code: str) -> Authenticator:
        try:
            device = Authenticator.objects.get(user=user, type=Authenticator.Type.TOTP)
        except Authenticator.DoesNotExist:
            logger.warning(f"MFA device not found for user {user.pk}")
            raise MFADeviceNotFoundError()

        if device.last_used_at:
            logger.warning(f"MFA device already confirmed for user {user.pk}")
            raise MFAAlreadyEnabledError()

        secret = device.data.get("secret")
        if not secret:
            raise MFADeviceNotFoundError()

        totp_instance = pyotp.TOTP(secret)
        if not totp_instance.verify(code):
            logger.warning(f"Invalid MFA code during activation for user {user.pk}")
            raise InvalidMFACodeError()

        from django.utils import timezone

        device.last_used_at = timezone.now()
        device.save()

        logger.info(f"MFA successfully activated for user {user.pk}")
        return device

    @staticmethod
    def deactivate_mfa(user: User) -> None:
        if not is_mfa_enabled(user):
            logger.warning(
                f"Attempted to deactivate MFA for user {user.pk} but it's not enabled"
            )
            raise MFANotEnabledError()

        try:
            device = Authenticator.objects.get(user=user, type=Authenticator.Type.TOTP)
            device.delete()
            logger.info(f"MFA successfully deactivated for user {user.pk}")
        except Authenticator.DoesNotExist:
            logger.error(f"MFA enabled but device not found for user {user.pk}")
            raise MFADeviceNotFoundError()
