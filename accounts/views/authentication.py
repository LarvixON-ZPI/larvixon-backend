from rest_framework import generics, status, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
import logging

# App's local imports
from ..models import User
from ..serializers import (
    UserSerializer,
    MFALoginSerializer,
)
from ..services.authentication import AuthenticationService
from ..errors import (
    MFARequiredError,
    InvalidMFACodeError,
    InvalidTokenError,
    MissingRefreshTokenError,
)

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Register new user",
    description="Register a new user account with email and password",
    responses={
        201: OpenApiResponse(description="User registered successfully"),
        400: OpenApiResponse(description="Validation error"),
    },
    tags=["Authentication"],
)
class UserRegistrationView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs) -> Response:
        user, tokens = AuthenticationService.register_user(request.data)

        return Response(
            {
                "user": UserSerializer(user).data,
                "refresh": tokens["refresh"],
                "access": tokens["access"],
                "message": "User registered successfully",
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary="User login with optional 2FA",
    description="Authenticate user with email/password. If 2FA is enabled, a second-factor code must be provided.",
    request=MFALoginSerializer,
    responses={
        200: OpenApiResponse(description="Login successful with or without 2FA"),
        400: OpenApiResponse(description="Invalid credentials or MFA code"),
        202: OpenApiResponse(description="MFA is required but not provided"),
    },
    tags=["Authentication"],
)
class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        mfa_code = request.data.get("mfa_code")

        try:
            user, tokens = AuthenticationService.login_user(email, password, mfa_code)
            return Response(
                {
                    "user": UserSerializer(user).data,
                    "refresh": tokens["refresh"],
                    "access": tokens["access"],
                    "message": "Login successful",
                },
                status=status.HTTP_200_OK,
            )
        except MFARequiredError:
            return Response(
                {"detail": "MFA is required."}, status=status.HTTP_202_ACCEPTED
            )
        except InvalidMFACodeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    def post(self, request) -> Response:
        refresh_token = request.data.get("refresh")

        try:
            AuthenticationService.logout_user(refresh_token)
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except MissingRefreshTokenError:
            logger.warning("Logout attempted without refresh token")
            return Response(
                {"error": "Refresh token not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidTokenError as e:
            logger.warning(f"Invalid token during logout: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SocialLoginJWTViewMixin:
    def post(self, request, *args, **kwargs):
        # Authenticate the user with the social provider (Google, Facebook, etc.)
        super().post(request, *args, **kwargs)
        user = request.user

        if not user.is_authenticated:
            logger.error("Social login failed - user not authenticated")
            return Response(
                {"error": "Social login failed. Authentication was not successful."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mfa_code = request.data.get("mfa_code")

        try:
            tokens = AuthenticationService.social_login(user, mfa_code)
            user_data = UserSerializer(user).data

            return Response(
                {
                    "user": user_data,
                    "access": tokens["access"],
                    "refresh": tokens["refresh"],
                    "message": "Social login successful",
                },
                status=status.HTTP_200_OK,
            )
        except MFARequiredError:
            return Response(
                {"detail": "MFA is required."}, status=status.HTTP_202_ACCEPTED
            )
        except InvalidMFACodeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Google social authentication",
    tags=["Authentication"],
    request=inline_serializer(
        name="GoogleLoginRequest",
        fields={
            "access_token": serializers.CharField(
                help_text="Google OAuth2 access token.", required=False
            ),
            "code": serializers.CharField(
                help_text="Google OAuth2 authorization code.", required=False
            ),
            "id_token": serializers.CharField(
                help_text="Google OAuth2 ID token.", required=False
            ),
            "mfa_code": serializers.CharField(
                help_text="2FA code required for MFA-enabled accounts.", required=False
            ),
        },
    ),
)
class GoogleLogin(SocialLoginJWTViewMixin, SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
