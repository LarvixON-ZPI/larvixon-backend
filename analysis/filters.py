import django_filters
from .models import VideoAnalysis

class VideoAnalysisFilter(django_filters.FilterSet):
    class Meta:
        model = VideoAnalysis
        fields = {
            'status': ['exact'],
            'actual_substance': ['exact', 'icontains'],
            # # Note: change confidence_scores to a numeric type in the model for this to work
            # 'confidence_scores': ['gt', 'lt', 'gte', 'lte'], 
        }