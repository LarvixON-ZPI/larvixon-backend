class AccountsError(Exception):
    """Base class for accounts-related errors."""

    pass


class MFAError(AccountsError):
    """Base class for MFA-related errors."""

    pass


class MFADeviceNotFoundError(MFAError):
    """Raised when an MFA device is not found for a user."""

    pass


class MFAAlreadyEnabledError(MFAError):
    """Raised when attempting to enable MFA for a user who already has it enabled."""

    pass


class MFANotEnabledError(MFAError):
    """Raised when attempting to deactivate MFA for a user who doesn't have it enabled."""

    pass


class MFADeviceNotConfirmedError(MFAError):
    """Raised when MFA device exists but is not confirmed yet."""

    pass


class InvalidMFACodeError(MFAError):
    """Raised when an invalid MFA code is provided."""

    def __init__(self, message: str = "Invalid MFA code"):
        self.message = message
        super().__init__(self.message)


class MFARequiredError(MFAError):
    """Raised when MFA is required but not provided."""

    pass


class AuthenticationError(AccountsError):
    """Base class for authentication-related errors."""

    pass


class InvalidTokenError(AuthenticationError):
    """Raised when an invalid token is provided."""

    def __init__(self, message: str = "Invalid token"):
        self.message = message
        super().__init__(self.message)


class MissingRefreshTokenError(AuthenticationError):
    """Raised when refresh token is missing."""

    pass


class SocialLoginFailedError(AuthenticationError):
    """Raised when social login authentication fails."""

    pass
