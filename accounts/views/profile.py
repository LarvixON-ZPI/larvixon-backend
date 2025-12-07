import logging

from rest_framework.request import Request
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiResponse

from accounts.models import User, UserProfile
from ..serializers import (
    UserSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
    UserStatsSerializer,
)
from ..services.profile import ProfileService

logger: logging.Logger = logging.getLogger(__name__)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserProfileDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    parser_classes = (MultiPartParser, FormParser)

    def get_object(self) -> UserProfile:
        user = self.request.user
        if not isinstance(user, User):
            raise TypeError("Authenticated user is not of type User")

        return ProfileService.get_or_create_profile(user)


class UserProfileStats(generics.RetrieveAPIView):
    serializer_class = UserStatsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self) -> dict[str, int]:
        user = self.request.user
        if not isinstance(user, User):
            raise TypeError("Authenticated user is not of type User")

        return ProfileService.get_user_stats(user)


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Change user password",
        description="Change the authenticated user's password.",
        request=PasswordChangeSerializer,
        responses={200: OpenApiResponse(description="Password changed successfully")},
        tags=["Authentication"],
    )
    def post(self, request: Request) -> Response:
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        user = self.request.user
        if not isinstance(user, User):
            raise TypeError("Authenticated user is not of type User")

        try:
            ProfileService.change_password(
                user, old_password, new_password, confirm_password
            )

            return Response(
                {"message": "Password changed successfully"}, status=status.HTTP_200_OK
            )
        except ValidationError as e:
            logger.error(f"Error changing password for user {user.pk}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
