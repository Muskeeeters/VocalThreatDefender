"""
api/serializers.py
==================
Django REST Framework serializers for VoiceShield AI.

AnalysisRequestSerializer  : Validates incoming multipart/form-data.
AnalysisResponseSerializer : Shapes the JSON response payload.
AnalysisRecordSerializer   : Full model serializer for admin/history views.
"""

import logging
from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from .models import AnalysisRecord

logger = logging.getLogger(__name__)

# Allowed audio MIME types and extensions
ALLOWED_EXTENSIONS = settings.ALLOWED_AUDIO_EXTENSIONS
ALLOWED_CONTENT_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/webm",
    "audio/mp4",
    "audio/x-m4a",
    "application/octet-stream",   # some browsers send this for blobs
}


class AnalysisRequestSerializer(serializers.Serializer):
    """
    Validates the POST /api/analyze/ request.

    At least one of ``audio_file`` or ``transcript`` must be provided.
    """

    audio_file = serializers.FileField(required=False, allow_null=True)
    transcript = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=5000,
        trim_whitespace=True,
    )

    def validate_audio_file(self, value):
        """Check file extension and rough size limit."""
        if value is None:
            return value

        ext = Path(value.name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported audio format '{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        max_size = settings.FILE_UPLOAD_MAX_MEMORY_SIZE
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Audio file too large ({value.size / 1_048_576:.1f} MB). "
                f"Maximum allowed: {max_size / 1_048_576:.0f} MB."
            )

        logger.debug("Audio file validated: %s (%d bytes)", value.name, value.size)
        return value

    def validate(self, attrs):
        """Ensure at least one input source is provided."""
        has_audio = bool(attrs.get("audio_file"))
        has_text = bool(attrs.get("transcript", "").strip())

        if not has_audio and not has_text:
            raise serializers.ValidationError(
                "Please provide at least one of: audio_file or transcript."
            )
        return attrs


class AnalysisResponseSerializer(serializers.Serializer):
    """
    Shapes the JSON payload returned by POST /api/analyze/.

    Example
    -------
    {
        "audio_risk": 42,
        "text_risk": 87,
        "final_score": 69,
        "verdict": "CRITICAL FRAUD",
        "recommendation": "Do not share OTPs or personal information.",
        "processing_ms": 1234
    }
    """

    audio_risk = serializers.FloatField(allow_null=True)
    text_risk = serializers.FloatField(allow_null=True)
    final_score = serializers.FloatField()
    verdict = serializers.CharField()
    recommendation = serializers.CharField()
    processing_ms = serializers.IntegerField()


class AnalysisRecordSerializer(serializers.ModelSerializer):
    """Full serializer for the AnalysisRecord model (used in admin/history)."""

    class Meta:
        model = AnalysisRecord
        fields = "__all__"
        read_only_fields = ("created_at",)