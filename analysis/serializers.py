from rest_framework import serializers
from .models import Substance, VideoAnalysis, AnalysisResult


class SubstanceSerializer(serializers.ModelSerializer):
    class Meta:  # type: ignore
        model = Substance
        fields = ("id", "name_en", "name_pl")
        read_only_fields = ("id", "name_en", "name_pl")


class AnalysisResultSerializer(serializers.ModelSerializer):
    substance = SubstanceSerializer(read_only=True)  # type: ignore

    class Meta:  # type: ignore
        model = AnalysisResult
        fields = ("id", "substance", "confidence_score", "detected_at")
        read_only_fields = ("id", "substance", "confidence_score", "detected_at")


class VideoAnalysisSerializer(serializers.ModelSerializer):
    """
    Serializer for video analysis records.
    """

    user = serializers.StringRelatedField(read_only=True)  # type: ignore

    analysis_results: AnalysisResultSerializer = AnalysisResultSerializer(
        many=True, read_only=True
    )
    thumbnail_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    video_name = serializers.SerializerMethodField()

    class Meta:  # type: ignore
        model = VideoAnalysis
        fields = (
            "id",
            "user",
            "title",
            "status",
            "video",
            "video_name",
            "video_url",
            "thumbnail",
            "thumbnail_url",
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
            "video_name",
            "video_url",
            "thumbnail_url",
        )

    def get_video_url(self, obj):
        if not obj.video:
            return None
        try:
            url = obj.video.url
        except ValueError:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    def get_thumbnail_url(self, obj):
        if not obj.thumbnail:
            return None
        try:
            url = obj.thumbnail.url
        except ValueError:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    def get_video_name(self, obj):
        if not obj.video:
            return None
        return obj.video.name.split("/")[-1]


class VideoAnalysisIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoAnalysis
        fields = ["id"]
        read_only_fields = ("id",)
