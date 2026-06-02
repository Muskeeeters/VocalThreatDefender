"""
voiceshield/urls.py
===================
Root URL configuration for the VoiceShield AI project.

Routes:
  /           → Frontend dashboard (index.html)
  /api/       → REST API endpoints
  /admin/     → Django admin panel
  /media/     → Uploaded file serving (dev only)
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ── Admin ─────────────────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── REST API ──────────────────────────────────────────────────────────────
    path("api/", include("api.urls")),

    # ── Frontend — serve index.html at root ───────────────────────────────────
    path("", TemplateView.as_view(template_name="index.html"), name="dashboard"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)