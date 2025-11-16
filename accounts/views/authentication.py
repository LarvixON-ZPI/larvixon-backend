from rest_framework_simplejwt.exceptions import TokenError
from rest_framework import generics, status, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.mfa.utils import is_mfa_enabled

# App's local imports
from ..models import User
from ..serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    MFALoginSerializer,
)
from ..utils import verify_mfa_code


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
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
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
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        if is_mfa_enabled(user):
            mfa_code = request.data.get("mfa_code")
            if not mfa_code:
                return Response(
                    {"detail": "MFA is required."}, status=status.HTTP_202_ACCEPTED
                )

            is_valid, error_message, _ = verify_mfa_code(user, mfa_code)
            if not is_valid:
                return Response(
                    {"detail": error_message}, status=status.HTTP_400_BAD_REQUEST
                )

        # If MFA is not enabled or the code was valid, issue tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "message": "Login successful",
            },
            status=status.HTTP_200_OK,
        )


class UserLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    def post(self, request) -> Response:
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except KeyError:
            return Response(
                {"error": "Refresh token not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TokenError:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
            )


class SocialLoginJWTViewMixin:
    def post(self, request, *args, **kwargs):
        # Authenticate the user with the social provider (Google, Facebook, etc.)
        super().post(request, *args, **kwargs)

        user = request.user

        if user.is_authenticated:
            # Check if MFA is enabled for this user after a successful social login
            if is_mfa_enabled(user):
                mfa_code = request.data.get("mfa_code")
                if not mfa_code:
                    return Response(
                        {"detail": "MFA is required."}, status=status.HTTP_202_ACCEPTED
                    )

                is_valid, error_message, _ = verify_mfa_code(user, mfa_code)
                if not is_valid:
                    return Response(
                        {"detail": error_message}, status=status.HTTP_400_BAD_REQUEST
                    )

            # If no MFA is enabled or the MFA code was valid, issue tokens
            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)

            user_data = UserSerializer(user).data

            return Response(
                {
                    "user": user_data,
                    "access": access,
                    "refresh": str(refresh),
                    "message": "Social login successful",
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": "Social login failed. Authentication was not successful."},
                status=status.HTTP_400_BAD_REQUEST,
            )


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
