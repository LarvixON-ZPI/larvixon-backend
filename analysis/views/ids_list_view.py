from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend
from analysis.models import VideoAnalysis
from ..serializers import VideoAnalysisIdSerializer
from ..filters import VideoAnalysisFilter

class VideoAnalysisIdListView(generics.ListAPIView):
    serializer_class = VideoAnalysisIdSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = VideoAnalysisFilter

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return VideoAnalysis.objects.none()
        return VideoAnalysis.objects.filter(user=self.request.user).only('id')