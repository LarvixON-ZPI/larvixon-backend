from rest_framework import serializers
from .models import Substance, VideoAnalysis, AnalysisResult


class SubstanceSerializer(serializers.ModelSerializer):
    class Meta:  # type: ignore
        model = Substance
        fields = ('id', 'name_en', 'name_pl')
        read_only_fields = ('id', 'name_en', 'name_pl')

class AnalysisResultSerializer(serializers.ModelSerializer):
    substance = SubstanceSerializer(read_only=True)  # type: ignore

    class Meta:  # type: ignore
        model = AnalysisResult
        fields = ('id', 'substance', 'confidence_score', 'detected_at')
        read_only_fields = ('id', 'substance', 'confidence_score', 'detected_at')

class VideoAnalysisSerializer(serializers.ModelSerializer):
    """
    Serializer for video analysis records.
    """

    user = serializers.StringRelatedField(read_only=True)  # type: ignore

    analysis_results: AnalysisResultSerializer = AnalysisResultSerializer(
        many=True, 
        read_only=True
    )

    class Meta:  # type: ignore
        model = VideoAnalysis
        fields = (
            "id",
            "user",
            "title",
            "status",
            "video_name",
            "created_at",
            "completed_at",
            "analysis_results",
            "actual_substance",
            "user_feedback",
        )
        read_only_fields = ("id", "user", "created_at", "completed_at", "analysis_results", "video_name")

class VideoAnalysisIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoAnalysis
        fields = ['id']
        read_only_fields = ('id',)