from rest_framework import generics, permissions
from analysis.models import VideoAnalysis
from .serializers import VideoAnalysisSerializer


class VideoAnalysisListView(generics.ListCreateAPIView):
    serializer_class = VideoAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VideoAnalysis.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class VideoAnalysisDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = VideoAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VideoAnalysis.objects.filter(user=self.request.user)
