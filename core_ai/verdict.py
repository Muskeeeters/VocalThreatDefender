import logging

logger = logging.getLogger(__name__)

# ── Verdict thresholds ────────────────────────────────────────────────────────
SAFE_MAX = 30
SUSPICIOUS_MAX = 60

# ── Verdict strings ───────────────────────────────────────────────────────────
VERDICT_SAFE = "SAFE"
VERDICT_SUSPICIOUS = "SUSPICIOUS"
VERDICT_CRITICAL = "CRITICAL FRAUD"

# ── Recommendation library ────────────────────────────────────────────────────
RECOMMENDATIONS = {
    VERDICT_SAFE: (
        "This interaction appears safe. No immediate threat detected. "
        "Always remain cautious — verify the identity of any caller who "
        "requests sensitive information, even if the call appears legitimate."
    ),
    VERDICT_SUSPICIOUS: (
        "This interaction contains suspicious patterns. Proceed with caution. "
        "Do NOT share personal details, passwords, or OTPs until you have "
        "independently verified the caller's identity through official channels. "
        "Consider ending the call and calling back using a verified number."
    ),
    VERDICT_CRITICAL: (
        "HIGH ALERT — This interaction has strong indicators of a Voice Phishing "
        "(Vishing) attack. Do NOT share any OTPs, passwords, card numbers, or "
        "personal information. Hang up immediately. Report this number to your "
        "bank's fraud hotline and to the relevant cybercrime authority. "
        "Do not call back on any number provided by the caller."
    ),
}


class VerdictEngine:
    """
    Converts a numeric risk percentage into a verdict and recommendation.

    Usage
    -----
    engine = VerdictEngine()
    result = engine.evaluate(78)
    # → {
    #       "risk_percentage": 78,
    #       "verdict": "CRITICAL FRAUD",
    #       "recommendation": "HIGH ALERT — ..."
    #   }
    """

    def __init__(
        self,
        safe_max: int = SAFE_MAX,
        suspicious_max: int = SUSPICIOUS_MAX,
    ):
        self._safe_max = safe_max
        self._suspicious_max = suspicious_max
        logger.info(
            "VerdictEngine initialised — thresholds: SAFE≤%d | SUSPICIOUS≤%d | CRITICAL>%d",
            safe_max,
            suspicious_max,
            suspicious_max,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate(self, risk_percentage: int | float) -> dict:
        """
        Evaluate a risk percentage and return a verdict dict.

        Parameters
        ----------
        risk_percentage : int | float
            Fused risk score in range [0, 100].

        Returns
        -------
        dict with keys:
            risk_percentage : int
            verdict         : str
            recommendation  : str
        """
        score = int(round(float(risk_percentage)))
        score = max(0, min(100, score))  # guard clamp

        verdict = self._classify(score)
        recommendation = RECOMMENDATIONS[verdict]

        logger.info("Verdict: %s (score=%d%%)", verdict, score)

        return {
            "risk_percentage": score,
            "verdict": verdict,
            "recommendation": recommendation,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _classify(self, score: int) -> str:
        """Apply threshold rules to produce a verdict string."""
        if score <= self._safe_max:
            return VERDICT_SAFE
        if score <= self._suspicious_max:
            return VERDICT_SUSPICIOUS
        return VERDICT_CRITICAL