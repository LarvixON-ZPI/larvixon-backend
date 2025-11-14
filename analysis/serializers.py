from typing import Any
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Substance, VideoAnalysis, AnalysisResult


class SubstanceSerializer(serializers.ModelSerializer):
    class Meta:  # type: ignore[misc]
        model = Substance
        fields = ("id", "name_en", "name_pl")
        read_only_fields = ("id", "name_en", "name_pl")


class AnalysisResultSerializer(serializers.ModelSerializer):
    substance = SubstanceSerializer(read_only=True)

    class Meta:  # type: ignore[misc]
        model = AnalysisResult
        fields = ("id", "substance", "confidence_score", "detected_at")
        read_only_fields = ("id", "substance", "confidence_score", "detected_at")


class VideoAnalysisSerializer(serializers.ModelSerializer):
    """
    Serializer for video analysis records.
    """

    user: Any = serializers.StringRelatedField(read_only=True)

    analysis_results = AnalysisResultSerializer(many=True, read_only=True)

    video_name = serializers.SerializerMethodField()

    class Meta:  # type: ignore[misc]
        model = VideoAnalysis
        fields = (
            "id",
            "user",
            "title",
            "status",
            "error_message",
            "video_name",
            "video",
            "thumbnail",
            "created_at",
            "completed_at",
            "analysis_results",
            "actual_substance",
            "user_feedback",
        )
        read_only_fields = (
            "id",
            "user",
            "created_at",
            "completed_at",
            "analysis_results",
            "error_message",
        )

    @extend_schema_field(OpenApiTypes.STR)
    def get_video_name(self, obj):
        if not obj.video:
            return None
        return obj.video.name.split("/")[-1]


class VideoAnalysisIdSerializer(serializers.ModelSerializer):
    class Meta:  # type: ignore[misc]
        model = VideoAnalysis
        fields = ["id"]
        read_only_fields = ("id",)
