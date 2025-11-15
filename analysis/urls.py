from django.urls import path
from django.urls.resolvers import URLPattern
from . import views

app_name = "analysis"

urlpatterns: list[URLPattern] = [
    path("", views.VideoAnalysisListView.as_view(), name="analysis-list"),
    path("<int:pk>/", views.VideoAnalysisDetailView.as_view(), name="analysis-detail"),
    path(
        "<int:pk>/retry/", views.VideoAnalysisRetryView.as_view(), name="analysis-retry"
    ),
    path("ids/", views.VideoAnalysisIdListView.as_view(), name="analysis-id-list"),
]
