from django.urls import path
from django.urls.resolvers import URLPattern
from .views import VideoUploadView

app_name = "videoprocessor"

urlpatterns: list[URLPattern] = [
    path("upload/", VideoUploadView.as_view(), name="video-upload"),
]
