"""
core_ai/text_analyzer.py
========================
MODULE 2 — Text Risk Analyzer
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

VISHING_LABELS = [
    "otp theft",
    "bank fraud",
    "account verification scam",
    "urgent payment request",
    "authority impersonation",
    "social engineering attack",
    "safe conversation",
]

SAFE_LABEL = "safe conversation"
DEFAULT_MODEL = "facebook/bart-large-mnli"

class TextRiskAnalyzer:
    def __init__(self, model_name: Optional[str] = None):
        self._model_name = model_name or self._resolve_model_name()
        self._pipeline = None
        self._lock = threading.Lock()
        logger.info("TextRiskAnalyzer initialised — model=%s", self._model_name)

    def analyze(self, transcript: str) -> dict:
        if not transcript or not transcript.strip():
            return {"text_risk": 0.1}

        truncated = self._truncate(transcript, max_words=600)
        
        logger.info(f"    [~] Target sequence parsed. Waking up NLP Pipeline ({self._model_name})...")
        pipeline = self._get_pipeline()

        logger.info(f"    [+] Pipeline active! Cross-referencing {len(VISHING_LABELS)} known cybercrime vectors...")

        try:
            result = pipeline(
                truncated,
                candidate_labels=VISHING_LABELS,
                multi_label=False,
            )
        except Exception as exc:
            raise RuntimeError(f"NLP classification failed: {exc}") from exc

        label_scores: dict[str, float] = dict(zip(result["labels"], result["scores"]))
        safe_prob = label_scores.get(SAFE_LABEL, 0.0)
        risk_score = float(1.0 - safe_prob)

        top_dangerous = max(
            (label for label in VISHING_LABELS if label != SAFE_LABEL),
            key=lambda l: label_scores.get(l, 0.0),
        )
        top_dangerous_score = label_scores.get(top_dangerous, 0.0)

        logger.info(f"    [!] NLP Primary Match: '{top_dangerous.upper()}' (Confidence: {top_dangerous_score:.2f})")

        return {"text_risk": float(min(risk_score, 1.0))}

    def _get_pipeline(self):
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    try:
                        from transformers import pipeline as hf_pipeline
                        import torch
                        device = 0 if torch.cuda.is_available() else -1
                        self._pipeline = hf_pipeline("zero-shot-classification", model=self._model_name, device=device)
                    except ImportError as exc:
                        raise ImportError("transformers and torch are required.") from exc
        return self._pipeline

    @staticmethod
    def _resolve_model_name() -> str:
        try:
            from django.conf import settings
            return settings.AI_CONFIG.get("NLP_MODEL", DEFAULT_MODEL)
        except Exception:
            return DEFAULT_MODEL

    @staticmethod
    def _truncate(text: str, max_words: int) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words])