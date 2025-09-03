from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
# Drf Spectacular imports
from drf_spectacular.utils import extend_schema, OpenApiResponse
# App's local imports
from ..models import User, UserProfile
from analysis.models import VideoAnalysis
from ..serializers import (
    UserSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
    UserStatsSerializer,
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
