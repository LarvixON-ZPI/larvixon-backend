from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend
from analysis.models import VideoAnalysis
from .serializers import VideoAnalysisSerializer
from .filters import VideoAnalysisFilter


class VideoAnalysisListView(generics.ListCreateAPIView):
    serializer_class = VideoAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = VideoAnalysisFilter  

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return VideoAnalysis.objects.none()
        return VideoAnalysis.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class VideoAnalysisDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = VideoAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VideoAnalysis.objects.filter(user=self.request.user)
