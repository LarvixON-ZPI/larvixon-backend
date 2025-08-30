from rest_framework_simplejwt.exceptions import TokenError
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from .models import User, UserProfile
from analysis.models import VideoAnalysis
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
    UserStatsSerializer
)


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
    summary="User login",
    description="Authenticate user with email and password",
    request=UserLoginSerializer,
    responses={
        200: OpenApiResponse(description="Login successful"),
        400: OpenApiResponse(description="Invalid credentials"),
    },
    tags=["Authentication"],
)
class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Generate tokens
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


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserProfileDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class UserProfileStats(generics.RetrieveAPIView):
    serializer_class = UserStatsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        analyses = VideoAnalysis.objects.filter(user=user)

        stats = {
            "total_analyses": analyses.count(),
            "completed_analyses": analyses.filter(status="completed").count(),
            "pending_analyses": analyses.filter(status="pending").count(),
            "processing_analyses": analyses.filter(status="processing").count(),
            "failed_analyses": analyses.filter(status="failed").count(),
        }

        return stats


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Change user password",
        description="Change the authenticated user's password.",
        request=PasswordChangeSerializer,
        responses={200: OpenApiResponse(description="Password changed successfully")},
        tags=["Authentication"],
    )
    def post(self, request) -> Response:
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user: User = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        return Response(
            {"message": "Password changed successfully"}, status=status.HTTP_200_OK
        )

class SocialLoginJWTViewMixin:
    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)

        user = request.user

        if user.is_authenticated:
            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)
            
            user_data = UserSerializer(user).data

            return Response({
                'user': user_data,
                'access': access,
                'refresh': str(refresh),
                'message': "Social login successful"
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Social login failed. Authentication was not successful."}, 
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(
    summary="Google social authentication",
    tags=["Authentication"],
)
class GoogleLogin(SocialLoginJWTViewMixin, SocialLoginView):
    adapter_class = GoogleOAuth2Adapter

@extend_schema(
    summary="Facebook social authentication idk if this works",
    tags=["Authentication"],
)
class FacebookLogin(SocialLoginJWTViewMixin, SocialLoginView):
    adapter_class = FacebookOAuth2Adapter