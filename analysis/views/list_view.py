from typing import Any
from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from analysis.models import VideoAnalysis
from ..serializers import VideoAnalysisSerializer
from ..filters import VideoAnalysisFilter
from patients.services import patient_service
import logging

logger = logging.getLogger(__name__)


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
        patient_guids = [
            str(analysis.patient_guid) for analysis in queryset if analysis.patient_guid
        ]

        if not patient_guids:
            context["patient_details_map"] = {}
            return context

        try:
            context["patient_details_map"] = patient_service.get_patients_by_guids(
                patient_guids
            )
        except Exception:
            logger.error(
                "Failed to fetch patient details for VideoAnalysisListView",
                exc_info=True,
            )
            context["patient_details_map"] = {}

        return context

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
