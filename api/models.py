"""
api/models.py
=============
Database models for VoiceShield AI.

AnalysisRecord stores every analysis request for audit trail and
future model retraining purposes.
"""

import logging
from django.db import models

logger = logging.getLogger(__name__)


class AnalysisRecord(models.Model):
    """
    Persists the result of each vishing analysis request.

    Fields
    ------
    created_at      : Timestamp of the request.
    audio_filename  : Original filename (if audio was supplied).
    transcript      : Text transcript (if supplied or transcribed).
    audio_risk      : Raw audio risk score  0–100 (None if no audio).
    text_risk       : Raw text risk score   0–100 (None if no text).
    final_score     : Fused risk percentage 0–100.
    verdict         : SAFE | SUSPICIOUS | CRITICAL FRAUD
    recommendation  : Human-readable advice string.
    processing_ms   : Server-side processing time in milliseconds.
    ip_address      : Requester IP (for rate-limiting & audit).
    """

    class Verdict(models.TextChoices):
        SAFE = "SAFE", "Safe"
        SUSPICIOUS = "SUSPICIOUS", "Suspicious"
        CRITICAL = "CRITICAL FRAUD", "Critical Fraud"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # ── Input fields ──────────────────────────────────────────────────────────
    audio_filename = models.CharField(max_length=255, blank=True, null=True)
    transcript = models.TextField(blank=True, null=True)

    # ── Score fields ──────────────────────────────────────────────────────────
    audio_risk = models.FloatField(blank=True, null=True)
    text_risk = models.FloatField(blank=True, null=True)
    final_score = models.FloatField()

    # ── Output fields ─────────────────────────────────────────────────────────
    verdict = models.CharField(
        max_length=20,
        choices=Verdict.choices,
        default=Verdict.SAFE,
    )
    recommendation = models.TextField(blank=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    processing_ms = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Analysis Record"
        verbose_name_plural = "Analysis Records"

    def __str__(self):
        return (
            f"[{self.created_at:%Y-%m-%d %H:%M:%S}] "
            f"{self.verdict} — {self.final_score:.1f}%"
        )