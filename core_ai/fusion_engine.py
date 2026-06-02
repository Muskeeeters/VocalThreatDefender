"""
core_ai/fusion_engine.py
========================
MODULE 3 — Score Fusion Engine

Combines the audio and text risk scores into a single fused percentage
using configurable weighted averaging.

Formula (default weights)
-------------------------
    final_score = (text_risk × 0.60) + (audio_risk × 0.40)

The result is converted to an integer percentage (0–100).

When only one source is available, the available score is used at full
weight so a meaningful result is always returned.

Output
------
{"final_score": 69}   ← integer percentage 0–100
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default fusion weights (must sum to 1.0)
DEFAULT_TEXT_WEIGHT = 0.60
DEFAULT_AUDIO_WEIGHT = 0.40


class ScoreFusionEngine:
    """
    Fuses audio and text risk scores into a single integer percentage.

    Parameters
    ----------
    text_weight : float
        Weight applied to the text risk score.  Default: 0.60
    audio_weight : float
        Weight applied to the audio risk score. Default: 0.40

    Both weights are normalised at runtime, so they do not need to
    sum exactly to 1.0 — but they should for predictable results.
    """

    def __init__(
        self,
        text_weight: float = DEFAULT_TEXT_WEIGHT,
        audio_weight: float = DEFAULT_AUDIO_WEIGHT,
    ):
        self._text_weight = text_weight
        self._audio_weight = audio_weight
        logger.info(
            "ScoreFusionEngine initialised — text_weight=%.2f, audio_weight=%.2f",
            text_weight,
            audio_weight,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def fuse(
        self,
        text_risk: Optional[float] = None,
        audio_risk: Optional[float] = None,
    ) -> dict:
        """
        Fuse risk scores into a final percentage.

        Parameters
        ----------
        text_risk : float | None
            NLP risk score in [0.0, 1.0].  None if no transcript was analysed.
        audio_risk : float | None
            Audio risk score in [0.0, 1.0]. None if no audio was analysed.

        Returns
        -------
        dict
            {"final_score": int}  where int ∈ [0, 100]

        Raises
        ------
        ValueError
            If both scores are None.
        """
        if text_risk is None and audio_risk is None:
            raise ValueError("At least one of text_risk or audio_risk must be provided.")

        # ── Determine effective weights ───────────────────────────────────────
        if text_risk is not None and audio_risk is not None:
            # Both sources available → use configured weights
            w_text = self._text_weight
            w_audio = self._audio_weight
            mode = "both"
        elif text_risk is not None:
            # Audio absent → text carries full weight
            w_text = 1.0
            w_audio = 0.0
            mode = "text_only"
        else:
            # Text absent → audio carries full weight
            w_text = 0.0
            w_audio = 1.0
            mode = "audio_only"

        # ── Normalise weights (safety guard) ─────────────────────────────────
        total_weight = w_text + w_audio
        if total_weight == 0:
            raise ValueError("Weights sum to zero — cannot normalise.")
        w_text /= total_weight
        w_audio /= total_weight

        # ── Compute fused score ───────────────────────────────────────────────
        t_score = text_risk if text_risk is not None else 0.0
        a_score = audio_risk if audio_risk is not None else 0.0

        raw_fused = (t_score * w_text) + (a_score * w_audio)
        final_pct = int(round(raw_fused * 100))
        final_pct = max(0, min(100, final_pct))  # clamp 0–100

        logger.info(
            "Score fusion [%s] — text=%.4f (w=%.2f), audio=%.4f (w=%.2f) → %d%%",
            mode,
            t_score,
            w_text,
            a_score,
            w_audio,
            final_pct,
        )

        return {"final_score": final_pct}