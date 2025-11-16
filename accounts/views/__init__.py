# accounts/views/__init__.py

from .authentication import (
    UserRegistrationView,
    UserLoginView,
    UserLogoutView,
    GoogleLogin,
)
from .profile import (
    UserProfileView,
    UserProfileDetailView,
    UserProfileStats,
    PasswordChangeView,
)
from .mfa import (
    MFASetupView,
    MFAVerifyView,
    MFADeactivateView,
)
