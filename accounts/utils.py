from allauth.mfa.models import Authenticator
from allauth.mfa import totp
import pyotp

def verify_mfa_code(user, mfa_code, is_confirmed_check=True):
    """
    Verifies an MFA code for a given user.
    `is_confirmed_check` determines if the device needs to be confirmed.
    Returns a tuple: (is_valid, error_message, device_object)
    """
    try:
        device = Authenticator.objects.get(user=user, type=Authenticator.Type.TOTP)
    except Authenticator.DoesNotExist:
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