from django.contrib import admin
from analysis.models import VideoAnalysis


@admin.register(VideoAnalysis)
class VideoAnalysisAdmin(admin.ModelAdmin):
    """
    Admin configuration for VideoAnalysis model.
    """

    list_display = ("user", "video_name", "status", "created_at", "completed_at")
    list_filter = ("status", "created_at", "completed_at")
    search_fields = ("user__email", "video_name", "actual_substance")
    readonly_fields = ("created_at", "completed_at")

    fieldsets = (
        ("Basic Info", {"fields": ("user", "video_name", "video_file_path", "status")}),
        ("Results", {"fields": ("results", "confidence_scores")}),
        ("User Feedback", {"fields": ("actual_substance", "user_feedback")}),
        ("Timestamps", {"fields": ("created_at", "completed_at")}),
    )

    def video_name(self, obj):
        if obj.video:
            return obj.video.name.split("/")[-1]
        return "(no file)"

    video_name.short_description = "Video Name"
