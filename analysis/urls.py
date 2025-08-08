from django.urls import path
from django.urls.resolvers import URLPattern
from . import views

app_name = 'analysis'

urlpatterns: list[URLPattern] = [
    path('', views.VideoAnalysisListView.as_view(), name='analysis-list'),
    path('<int:pk>/', views.VideoAnalysisDetailView.as_view(),
         name='analysis-detail'),
]
