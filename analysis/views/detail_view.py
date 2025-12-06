import logging
from rest_framework import generics, permissions
from analysis.models import VideoAnalysis
from ..serializers import VideoAnalysisSerializer
from patients.services.patients import patient_service

logger: logging.Logger = logging.getLogger(__name__)


class VideoAnalysisDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = VideoAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VideoAnalysis.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()

        obj = self.get_object()
        if not obj.patient_guid:
            context["patient_details_map"] = {}
            return context

        try:
            patient_details = patient_service.get_patient_by_guid(str(obj.patient_guid))
            if patient_details:
                context["patient_details_map"] = {
                    str(obj.patient_guid): patient_details
                }
            else:
                context["patient_details_map"] = {}
        except Exception:
            logger.error(
                "Failed to fetch patient details for VideoAnalysisDetailView",
                exc_info=True,
            )
            context["patient_details_map"] = {}

        return context
