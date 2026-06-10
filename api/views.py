"""
api/views.py
============
REST API views for VoiceShield AI.

AnalyzeView   : POST /api/analyze/  — core analysis endpoint.
HealthView    : GET  /api/health/   — liveness probe.
HistoryView   : GET  /api/history/  — last 20 analysis records.
"""

import logging
import os
import time
import tempfile
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AnalysisRecord
from .serializers import (
    AnalysisRequestSerializer,
    AnalysisResponseSerializer,
    AnalysisRecordSerializer,
)
from core_ai.audio_analyzer import AudioRiskAnalyzer
from core_ai.text_analyzer import TextRiskAnalyzer
from core_ai.fusion_engine import ScoreFusionEngine
from core_ai.verdict import VerdictEngine

logger = logging.getLogger(__name__)

# ── Singleton AI engine instances (loaded once at startup) ────────────────────
_audio_analyzer = AudioRiskAnalyzer()
_text_analyzer = TextRiskAnalyzer()
_fusion_engine = ScoreFusionEngine()
_verdict_engine = VerdictEngine()


def _get_client_ip(request) -> str | None:
    """Extract the real client IP, handling proxy headers."""
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AnalyzeView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        start_time = time.perf_counter()

        logger.info("\n" + "="*60)
        logger.info("🛡️  VOICESHIELD AI — NEW THREAT ANALYSIS INITIATED")
        logger.info("="*60)

        # ── 1. Validate input ─────────────────────────────────────────────────
        serializer = AnalysisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Invalid request: %s", serializer.errors)
            return Response(
                {"error": "Invalid request.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated = serializer.validated_data
        audio_file = validated.get("audio_file")
        transcript = validated.get("transcript", "").strip()

        logger.info(f"[+] Connection securely established from IP: {_get_client_ip(request)}")
        logger.info(f"[+] Payload specs — Audio Attached: {bool(audio_file)} | Transcript Attached: {bool(transcript)}")

        # ── 2. Audio analysis ─────────────────────────────────────────────────
        audio_risk_score: float | None = None
        audio_filename: str | None = None
        tmp_path: str | None = None

        if audio_file:
            logger.info("\n>>> STEP 1: INITIALIZING AUDIO FORENSICS ENGINE")
            audio_filename = audio_file.name
            try:
                suffix = Path(audio_file.name).suffix.lower() or ".wav"
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=suffix,
                    dir=settings.AI_CONFIG["TEMP_UPLOAD_DIR"],
                ) as tmp:
                    for chunk in audio_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name

                logger.info(f"    [+] Audio stream saved to secure vault: {audio_filename}")
                logger.info("    [+] Routing stream to Librosa AudioRiskAnalyzer...")
                
                result = _audio_analyzer.analyze(tmp_path)
                audio_risk_score = result["audio_risk"]
                logger.info(f"    [!] AUDIO RISK EVALUATION: {audio_risk_score * 100:.2f}%")

            except Exception as exc:
                logger.error("Audio analysis failed: %s", exc, exc_info=True)
                return Response(
                    {"error": f"Audio analysis failed: {str(exc)}"},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError as e:
                        logger.warning("Could not remove temp file %s: %s", tmp_path, e)

        # ── 3. Text analysis ──────────────────────────────────────────────────
        text_risk_score: float | None = None

        if transcript:
            logger.info("\n>>> STEP 2: INITIALIZING NLP THREAT DETECTION")
            try:
                logger.info("    [+] Routing transcript to TextRiskAnalyzer...")
                result = _text_analyzer.analyze(transcript)
                text_risk_score = result["text_risk"]
                logger.info(f"    [!] NLP INTENT RISK EVALUATION: {text_risk_score * 100:.2f}%")
            except Exception as exc:
                logger.error("Text analysis failed: %s", exc, exc_info=True)
                return Response(
                    {"error": f"Text analysis failed: {str(exc)}"},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

        # ── 4. Score fusion ───────────────────────────────────────────────────
        logger.info("\n>>> STEP 3: FUSING MULTI-MODAL METRICS")
        try:
            fused = _fusion_engine.fuse(
                audio_risk=audio_risk_score,
                text_risk=text_risk_score,
            )
            final_score = fused["final_score"]
            logger.info(f"    [+] Score Fusion Engine returned normalized threat value: {final_score}%")
        except Exception as exc:
            logger.error("Score fusion failed: %s", exc, exc_info=True)
            return Response(
                {"error": "Score fusion failed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── 5. Verdict generation ─────────────────────────────────────────────
        verdict_data = _verdict_engine.evaluate(final_score)

        # ── 6. Persist to database ────────────────────────────────────────────
        processing_ms = int((time.perf_counter() - start_time) * 1000)

        try:
            AnalysisRecord.objects.create(
                audio_filename=audio_filename,
                transcript=transcript or None,
                audio_risk=round(audio_risk_score * 100, 2) if audio_risk_score is not None else None,
                text_risk=round(text_risk_score * 100, 2) if text_risk_score is not None else None,
                final_score=final_score,
                verdict=verdict_data["verdict"],
                recommendation=verdict_data["recommendation"],
                processing_ms=processing_ms,
                ip_address=_get_client_ip(request),
            )
            logger.info("    [+] Forensics data committed to audit log.")
        except Exception as exc:
            logger.error("Failed to persist analysis record: %s", exc, exc_info=True)

        # ── 7. Build & return response ────────────────────────────────────────
        payload = {
            "audio_risk": round(audio_risk_score * 100, 1) if audio_risk_score is not None else None,
            "text_risk": round(text_risk_score * 100, 1) if text_risk_score is not None else None,
            "final_score": final_score,
            "verdict": verdict_data["verdict"],
            "recommendation": verdict_data["recommendation"],
            "processing_ms": processing_ms,
        }

        logger.info("="*60)
        logger.info(f"🏁 ANALYSIS COMPLETE | VERDICT: {verdict_data['verdict']} | TIME: {processing_ms}ms")
        logger.info("="*60 + "\n")

        response_serializer = AnalysisResponseSerializer(data=payload)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.validated_data, status=status.HTTP_200_OK)


class HealthView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({"status": "ok", "service": "VoiceShield AI", "version": "1.0.0"}, status=status.HTTP_200_OK)

class HistoryView(APIView):
    def get(self, request, *args, **kwargs):
        records = AnalysisRecord.objects.all()[:20]
        serializer = AnalysisRecordSerializer(records, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})