from rest_framework import serializers
from .models import VideoAnalysis


class VideoAnalysisSerializer(serializers.ModelSerializer):
    """
    Serializer for video analysis records.
    """

    user = serializers.StringRelatedField(read_only=True)  # type: ignore

    class Meta:  # type: ignore
        model = VideoAnalysis
        fields = (
            "id",
            "user",
            "video_name",
            "status",
            "created_at",
            "completed_at",
            "results",
            "confidence_scores",
            "actual_substance",
            "user_feedback",
        )
        read_only_fields = ("id", "user", "created_at", "completed_at")

class VideoAnalysisIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoAnalysis
        fields = ['id']
        read_only_fields = ('id',)