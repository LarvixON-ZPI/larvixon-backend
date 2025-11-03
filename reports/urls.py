from django.urls import path
from .views import AnalysisReportView

urlpatterns = [
    path(
        "analysis/<int:pk>/pdf/",
        AnalysisReportView.as_view(),
        name="analysis-report",
    ),
]
