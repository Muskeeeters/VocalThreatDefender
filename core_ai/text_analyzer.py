"""
core_ai/text_analyzer.py
========================
MODULE 2 — Text Risk Analyzer

Uses HuggingFace ``facebook/bart-large-mnli`` zero-shot classification
to score a voice call transcript for vishing / social-engineering intent.

Architecture
------------
* Zero-shot pipeline with 7 candidate labels covering common vishing tactics.
* The "safe conversation" label acts as a negative class anchor.
* Risk score = 1 − P("safe conversation").
* Lazy model loading on first call to avoid slowing Django startup.

Output
------
{"text_risk": 0.83}   ← float, 0 = safe, 1 = high risk
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# ── Vishing intent labels ─────────────────────────────────────────────────────
VISHING_LABELS = [
    "otp theft",
    "bank fraud",
    "account verification scam",
    "urgent payment request",
    "authority impersonation",
    "social engineering attack",
    "safe conversation",
]

# Label used as the "negative / benign" class
SAFE_LABEL = "safe conversation"

# Default model — can be overridden via settings.AI_CONFIG["NLP_MODEL"]
DEFAULT_MODEL = "facebook/bart-large-mnli"


class TextRiskAnalyzer:
    """
    Classifies a call transcript for vishing intent using zero-shot NLI.

    Usage
    -----
    analyzer = TextRiskAnalyzer()
    result = analyzer.analyze("Your OTP is required immediately.")
    # → {"text_risk": 0.91}
    """

    def __init__(self, model_name: Optional[str] = None):
        self._model_name = model_name or self._resolve_model_name()
        self._pipeline = None
        self._lock = threading.Lock()
        logger.info("TextRiskAnalyzer initialised — model=%s (lazy load)", self._model_name)

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, transcript: str) -> dict:
        """
        Analyse a text transcript and return a risk dict.

        Parameters
        ----------
        transcript : str
            The voice call transcript to evaluate.

        Returns
        -------
        dict
            {"text_risk": float}  where float ∈ [0.0, 1.0]
        """
        if not transcript or not transcript.strip():
            logger.warning("Empty transcript submitted — returning neutral score.")
            return {"text_risk": 0.1}

        # Truncate extremely long transcripts (BART max 1024 tokens ≈ 800 words)
        truncated = self._truncate(transcript, max_words=600)

        pipeline = self._get_pipeline()

        logger.debug("Running zero-shot classification on %d chars", len(truncated))

        try:
            result = pipeline(
                truncated,
                candidate_labels=VISHING_LABELS,
                multi_label=False,
            )
        except Exception as exc:
            raise RuntimeError(f"NLP classification failed: {exc}") from exc

        # Map label → score
        label_scores: dict[str, float] = dict(zip(result["labels"], result["scores"]))
        logger.debug("Label scores: %s", label_scores)

        # Risk = complement of "safe conversation" probability
        safe_prob = label_scores.get(SAFE_LABEL, 0.0)
        risk_score = float(1.0 - safe_prob)

        # Boost: if the top dangerous label has a very high score, amplify
        top_dangerous = max(
            (label for label in VISHING_LABELS if label != SAFE_LABEL),
            key=lambda l: label_scores.get(l, 0.0),
        )
        top_dangerous_score = label_scores.get(top_dangerous, 0.0)

        logger.info(
            "Text risk: %.4f | safe_prob=%.4f | top_label='%s' (%.4f)",
            risk_score,
            safe_prob,
            top_dangerous,
            top_dangerous_score,
        )

        return {"text_risk": float(min(risk_score, 1.0))}

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_pipeline(self):
        """
        Lazily load the HuggingFace pipeline on the first call.
        Thread-safe via a lock so Django's multi-threaded dev server
        doesn't load the model twice.
        """
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    logger.info("Loading NLP model: %s …", self._model_name)
                    try:
                        from transformers import pipeline as hf_pipeline
                        import torch

                        device = 0 if torch.cuda.is_available() else -1
                        logger.info(
                            "Using device: %s",
                            "CUDA GPU" if device == 0 else "CPU",
                        )

                        self._pipeline = hf_pipeline(
                            "zero-shot-classification",
                            model=self._model_name,
                            device=device,
                        )
                        logger.info("NLP model loaded successfully.")
                    except ImportError as exc:
                        raise ImportError(
                            "transformers and torch are required. "
                            "Install with: pip install transformers torch"
                        ) from exc
                    except Exception as exc:
                        raise RuntimeError(
                            f"Failed to load NLP model '{self._model_name}': {exc}"
                        ) from exc
        return self._pipeline

    @staticmethod
    def _resolve_model_name() -> str:
        """Read model name from Django settings if available."""
        try:
            from django.conf import settings
            return settings.AI_CONFIG.get("NLP_MODEL", DEFAULT_MODEL)
        except Exception:
            return DEFAULT_MODEL

    @staticmethod
    def _truncate(text: str, max_words: int) -> str:
        """Truncate text to ``max_words`` words."""
        words = text.split()
        if len(words) <= max_words:
            return text
        truncated = " ".join(words[:max_words])
        logger.debug("Transcript truncated from %d to %d words.", len(words), max_words)
        return truncated