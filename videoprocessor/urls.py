from django.urls import path
from django.urls.resolvers import URLPattern
from .views import VideoUploadView, ChunkedUploadView

app_name = "videoprocessor"

urlpatterns: list[URLPattern] = [
    path("upload/", VideoUploadView.as_view(), name="video-upload"),
    path("upload-chunk/", ChunkedUploadView.as_view(), name="video-upload-chunked"),
]
