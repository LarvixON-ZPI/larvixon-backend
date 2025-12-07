from typing import Any
from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from analysis.models import VideoAnalysis
from analysis.services.analysis import AnalysisService
from ..serializers import VideoAnalysisSerializer
from ..filters import VideoAnalysisFilter
import logging

logger: logging.Logger = logging.getLogger(__name__)


class VideoAnalysisListView(generics.ListCreateAPIView):
    serializer_class = VideoAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends: Any = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = VideoAnalysisFilter

    ordering_fields = ["description", "created_at", "completed_at", "status"]

    ordering = ["-created_at"]  # default ordering

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return VideoAnalysis.objects.none()
        return VideoAnalysis.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()

        queryset = self.filter_queryset(self.get_queryset())
        patient_details_map = AnalysisService.get_patients_details_map(list(queryset))
        context["patient_details_map"] = patient_details_map

        return context

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
