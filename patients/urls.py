from django.urls import path
from .views import GetPatientView, SearchPatientsView

app_name = "patients"

urlpatterns = [
    path(
        "",
        SearchPatientsView.as_view(),
        name="patient-list",
    ),
    path(
        "<str:guid>/",
        GetPatientView.as_view(),
        name="patient-detail",
    ),
]
