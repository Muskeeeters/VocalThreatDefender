"""
api/admin.py
============
Django admin configuration for VoiceShield AI.

Registers the AnalysisRecord model with a rich list display,
filters, and search capability for operational monitoring.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import AnalysisRecord


@admin.register(AnalysisRecord)
class AnalysisRecordAdmin(admin.ModelAdmin):
    """Admin panel for analysing and reviewing detection records."""

    list_display = (
        "created_at",
        "verdict_badge",
        "final_score_display",
        "audio_risk",
        "text_risk",
        "audio_filename",
        "processing_ms",
        "ip_address",
    )

    list_filter = ("verdict", "created_at")

    search_fields = ("transcript", "audio_filename", "ip_address")

    readonly_fields = (
        "created_at",
        "audio_risk",
        "text_risk",
        "final_score",
        "verdict",
        "recommendation",
        "processing_ms",
        "ip_address",
    )

    ordering = ("-created_at",)

    fieldsets = (
        ("Input", {
            "fields": ("audio_filename", "transcript"),
        }),
        ("Risk Scores", {
            "fields": ("audio_risk", "text_risk", "final_score"),
        }),
        ("Verdict", {
            "fields": ("verdict", "recommendation"),
        }),
        ("Metadata", {
            "fields": ("created_at", "processing_ms", "ip_address"),
        }),
    )

    def verdict_badge(self, obj):
        """Colour-coded verdict for the list display."""
        colours = {
            "SAFE": "#27ae60",
            "SUSPICIOUS": "#f39c12",
            "CRITICAL FRAUD": "#e74c3c",
        }
        colour = colours.get(obj.verdict, "#7f8c8d")
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;'
            'border-radius:4px;font-weight:bold;">{}</span>',
            colour,
            obj.verdict,
        )
    verdict_badge.short_description = "Verdict"
    verdict_badge.admin_order_field = "verdict"

    def final_score_display(self, obj):
        return f"{obj.final_score:.1f}%"
    final_score_display.short_description = "Score"
    final_score_display.admin_order_field = "final_score"