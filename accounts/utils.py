import os
import uuid
import logging
from allauth.mfa.models import Authenticator
from allauth.mfa import totp
import pyotp

logger = logging.getLogger(__name__)


def verify_mfa_code(user, mfa_code, is_confirmed_check=True):
    """
    Verifies an MFA code for a given user.
    `is_confirmed_check` determines if the device needs to be confirmed.
    Returns a tuple: (is_valid, error_message, device_object)
    """
    try:
        device = Authenticator.objects.get(user=user, type=Authenticator.Type.TOTP)
    except Authenticator.DoesNotExist:
        logger.warning(f"MFA device not found for user {user.id}")
        return False, "MFA device not found.", None

    if is_confirmed_check and not device.last_used_at:
        return False, "MFA device is not confirmed.", device

    secret = device.data.get("secret")
    if not secret:
        return False, "MFA secret key not found.", device

    totp_instance = pyotp.TOTP(secret)
    if not totp_instance.verify(mfa_code):
        return False, "Invalid MFA code.", device

    return True, None, device


def get_user_folder(user) -> str:
    return f"users/{user.pk}/"


def user_video_upload_to(instance, filename):
    # eg. users/1/videos/<hex>/videoname.mp4
    unique_folder = uuid.uuid4().hex
    folder = f"{get_user_folder(instance.user)}/videos/{unique_folder}"
    return os.path.join(folder, filename)


def user_thumbnail_upload_to(instance, filename):
    # eg. users/1/videos/<hex>/videoname.jpg
    video_path = instance.video.name
    folder = os.path.dirname(video_path)
    base_name, _ = os.path.splitext(os.path.basename(video_path))
    thumbnail_name = f"{base_name}_thumb.png"
    return os.path.join(folder, thumbnail_name)


def user_picture_upload_to(instance, filename):
    folder = f"{get_user_folder(instance.user)}/profile"
    return os.path.join(folder, filename)
