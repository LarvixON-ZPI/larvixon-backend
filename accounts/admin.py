from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile
from analysis.models import VideoAnalysis


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin configuration for User model.
    """
    list_display = ('email', 'username', 'first_name',
                    'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for UserProfile model.
    """
    list_display = ('user', 'organization', 'phone_number', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'user__username',
                     'organization', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(VideoAnalysis)
class VideoAnalysisAdmin(admin.ModelAdmin):
    """
    Admin configuration for VideoAnalysis model.
    """
    list_display = ('user', 'video_name', 'status',
                    'created_at', 'completed_at')
    list_filter = ('status', 'created_at', 'completed_at')
    search_fields = ('user__email', 'video_name', 'actual_substance')
    readonly_fields = ('created_at', 'completed_at')

    fieldsets = (
        ('Basic Info', {
         'fields': ('user', 'video_name', 'video_file_path', 'status')}),
        ('Results', {'fields': ('results', 'confidence_scores')}),
        ('User Feedback', {'fields': ('actual_substance', 'user_feedback')}),
        ('Timestamps', {'fields': ('created_at', 'completed_at')}),
    )
