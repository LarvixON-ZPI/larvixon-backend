from django.urls import path
from django.urls.resolvers import URLPattern
from . import views

app_name = 'accounts'

urlpatterns: list[URLPattern] = [
    # Authentication endpoints
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),

    # User profile endpoints
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/details/', views.UserProfileDetailView.as_view(),
         name='profile-details'),
    path('password/change/', views.PasswordChangeView.as_view(),
         name='password-change'),
    path('stats/', views.user_stats, name='user-stats'),
]
