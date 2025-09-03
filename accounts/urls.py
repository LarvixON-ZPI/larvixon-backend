from django.urls import path
from django.urls.resolvers import URLPattern
from . import views

app_name = "accounts"

urlpatterns: list[URLPattern] = [
    # Authentication endpoints
    path("register/", views.UserRegistrationView.as_view(), name="register"),
    path('auth/google/', views.GoogleLogin.as_view(), name='google_login'),
    path('auth/facebook/', views.FacebookLogin.as_view(), name='facebook_login'),
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    # 2FA Endpoints
    path("mfa/setup/", views.MFASetupView.as_view(), name="mfa_setup"),
    path("mfa/verify/", views.MFAVerifyView.as_view(), name="mfa_verify"),
    path("mfa/deactivate/", views.MFADeactivateView.as_view(), name="mfa_deactivate"),
    # User profile endpoints
    path("profile/", views.UserProfileView.as_view(), name="profile"),
    path(
        "profile/details/",
        views.UserProfileDetailView.as_view(),
        name="profile-details",
    ),
    path(
        "password/change/", views.PasswordChangeView.as_view(), name="password-change"
    ),
    path("profile/stats/", views.UserProfileStats.as_view(), name="user-stats"),
]
