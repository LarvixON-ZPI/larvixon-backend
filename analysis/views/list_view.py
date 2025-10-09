from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from analysis.models import VideoAnalysis
from ..serializers import VideoAnalysisSerializer
from ..filters import VideoAnalysisFilter


class VideoAnalysisListView(generics.ListCreateAPIView):
    serializer_class = VideoAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = VideoAnalysisFilter  

    ordering_fields = ['title', 'created_at', 'completed_at', 'status']

    ordering = ['-created_at'] # default ordering

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return VideoAnalysis.objects.none()
        return VideoAnalysis.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
