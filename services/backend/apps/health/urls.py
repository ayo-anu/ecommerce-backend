from django.urls import path
from . import views

app_name = 'health'

urlpatterns = [
    path('live/', views.liveness_check, name='liveness'),
    path('ready/', views.readiness_check, name='readiness'),
    path('', views.health_check, name='health'),
]
