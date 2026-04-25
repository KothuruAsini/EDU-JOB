# api/urls.py
from django.urls import path
from .views import (
    register_view,
    login_view,
    profile_view,
    predict_view,
    history_view,
    history_delete_view,
    logout_view,
)


urlpatterns = [
    path('register/', register_view),
    path('login/', login_view),
    path('logout/', logout_view),
    path('profile/', profile_view),
    path('predict/', predict_view),
    path('parse_resume/', __import__('api.views', fromlist=['parse_resume_view']).parse_resume_view),
    path('history/', history_view),
    path('history/<int:history_id>/', history_delete_view),
]
