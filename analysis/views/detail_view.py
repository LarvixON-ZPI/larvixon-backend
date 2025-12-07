import logging
from rest_framework import generics, permissions
from analysis.models import VideoAnalysis
from ..serializers import VideoAnalysisSerializer
from ..services.analysis import AnalysisService

logger: logging.Logger = logging.getLogger(__name__)


class VideoAnalysisDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = VideoAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VideoAnalysis.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()

        obj = self.get_object()
        patient_details_map = AnalysisService.get_patient_details_for_analysis(obj)
        context["patient_details_map"] = patient_details_map

        return context
