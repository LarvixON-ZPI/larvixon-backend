from django.urls import path
from django.urls.resolvers import URLPattern
from videoprocessor.views.upload import VideoUploadView

app_name = "videoprocessor"

urlpatterns: list[URLPattern] = [
    path("upload/", VideoUploadView.as_view(), name="video-upload"),
]