"""
api/urls.py
===========
URL patterns for the VoiceShield AI REST API.

Endpoints
---------
POST /api/analyze/    → core vishing analysis
GET  /api/health/     → liveness probe
GET  /api/history/    → recent analysis records
"""

from django.urls import path
from .views import AnalyzeView, HealthView, HistoryView
app_name = "api"
urlpatterns = [
    path("analyze/", AnalyzeView.as_view(), name="analyze"),
    path("health/", HealthView.as_view(), name="health"),
    path("history/", HistoryView.as_view(), name="history"),
]