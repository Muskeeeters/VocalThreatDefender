"""
core_ai/audio_analyzer.py
==========================
MODULE 1 — Audio Risk Analyzer

Analyses an audio file for characteristics common in synthetic / deepfake
voice phishing calls using Librosa MFCC feature extraction.

Design choices
--------------
* Resamples every file to 16 000 Hz (telephony standard).
* Extracts 40 MFCC coefficients and their first-order deltas.
* Computes multiple heuristics:
    - Low spectral variance → flat / synthesized speech
    - Abnormal pitch range  → TTS artefacts
    - Silence ratio         → scripted pauses
    - MFCC delta energy     → unnatural prosody
* Combines heuristics into a single [0.0, 1.0] risk float via
  weighted average and sigmoid normalisation.

Output
------
{"audio_risk": 0.42}   ← float, 0 = safe, 1 = high risk
"""

import logging
import warnings
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Suppress noisy librosa/audioread warnings during feature extraction
warnings.filterwarnings("ignore", category=UserWarning, module="librosa")
warnings.filterwarnings("ignore", category=FutureWarning, module="librosa")

# Target sample rate (telephony standard)
TARGET_SR = 16_000

# MFCC configuration
N_MFCC = 40
HOP_LENGTH = 512
N_FFT = 1024


def _sigmoid(x: float, k: float = 8.0, x0: float = 0.5) -> float:
    """Sigmoid squasher — maps any real number to (0, 1)."""
    return 1.0 / (1.0 + np.exp(-k * (x - x0)))


class AudioRiskAnalyzer:
    """
    Analyses audio files for vishing / deepfake characteristics.

    Usage
    -----
    analyzer = AudioRiskAnalyzer()
    result = analyzer.analyze("/path/to/call.wav")
    # → {"audio_risk": 0.73}
    """

    def __init__(self):
        logger.info("AudioRiskAnalyzer initialised (target_sr=%d Hz)", TARGET_SR)

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, file_path: str) -> dict:
        """
        Analyse an audio file and return a risk dict.

        Parameters
        ----------
        file_path : str
            Absolute path to a .wav / .mp3 / .ogg / .webm file.

        Returns
        -------
        dict
            {"audio_risk": float}  where float ∈ [0.0, 1.0]
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        logger.debug("Loading audio: %s", path.name)

        try:
            import librosa  # lazy import — not needed at startup
        except ImportError as exc:
            raise ImportError(
                "librosa is required for audio analysis. "
                "Install it with: pip install librosa"
            ) from exc

        # ── Load & resample ───────────────────────────────────────────────────
        try:
            audio, sr = librosa.load(str(path), sr=TARGET_SR, mono=True)
        except Exception as exc:
            raise ValueError(f"Could not load audio file '{path.name}': {exc}") from exc

        duration = len(audio) / sr
        logger.debug("Loaded: %.2f seconds at %d Hz", duration, sr)

        if duration < 0.5:
            logger.warning("Audio too short (%.2fs) — returning neutral score", duration)
            return {"audio_risk": 0.3}

        # ── Feature extraction ────────────────────────────────────────────────
        features = self._extract_features(audio, sr, librosa)

        # ── Heuristic scoring ─────────────────────────────────────────────────
        risk_score = self._compute_risk(features, duration)

        logger.info("Audio risk score: %.4f (file=%s)", risk_score, path.name)
        return {"audio_risk": float(np.clip(risk_score, 0.0, 1.0))}

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_features(self, audio: np.ndarray, sr: int, librosa) -> dict:
        """Extract acoustic features used for risk heuristics."""
        features = {}

        # 1. MFCCs
        mfcc = librosa.feature.mfcc(
            y=audio, sr=sr, n_mfcc=N_MFCC, hop_length=HOP_LENGTH, n_fft=N_FFT
        )
        features["mfcc"] = mfcc
        features["mfcc_mean"] = np.mean(mfcc, axis=1)
        features["mfcc_std"] = np.std(mfcc, axis=1)
        features["mfcc_var_mean"] = float(np.mean(np.var(mfcc, axis=1)))

        # 2. Delta MFCCs (first derivative — captures rate of change)
        delta_mfcc = librosa.feature.delta(mfcc)
        features["delta_energy"] = float(np.mean(np.abs(delta_mfcc)))

        # 3. Spectral features
        spec_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr, hop_length=HOP_LENGTH)
        features["spectral_centroid_std"] = float(np.std(spec_centroid))

        spec_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr, hop_length=HOP_LENGTH)
        features["spectral_rolloff_std"] = float(np.std(spec_rolloff))

        # 4. Zero-crossing rate (higher in synthetic voice)
        zcr = librosa.feature.zero_crossing_rate(audio, hop_length=HOP_LENGTH)
        features["zcr_mean"] = float(np.mean(zcr))
        features["zcr_std"] = float(np.std(zcr))

        # 5. RMS energy (silence ratio)
        rms = librosa.feature.rms(y=audio, hop_length=HOP_LENGTH)[0]
        silence_threshold = 0.01 * np.max(rms) if np.max(rms) > 0 else 0.0
        features["silence_ratio"] = float(np.mean(rms < silence_threshold))
        features["rms_std"] = float(np.std(rms))

        # 6. Fundamental frequency (pitch) via YIN
        try:
            f0, voiced_flag, _ = librosa.pyin(
                audio,
                fmin=librosa.note_to_hz("C2"),
                fmax=librosa.note_to_hz("C7"),
                sr=sr,
            )
            voiced_f0 = f0[voiced_flag] if voiced_flag is not None else np.array([])
            if len(voiced_f0) > 0:
                features["pitch_range"] = float(np.max(voiced_f0) - np.min(voiced_f0))
                features["pitch_std"] = float(np.std(voiced_f0))
                features["voiced_ratio"] = float(np.mean(voiced_flag))
            else:
                features["pitch_range"] = 0.0
                features["pitch_std"] = 0.0
                features["voiced_ratio"] = 0.0
        except Exception:
            features["pitch_range"] = 0.0
            features["pitch_std"] = 0.0
            features["voiced_ratio"] = 0.5

        return features

    def _compute_risk(self, f: dict, duration: float) -> float:
        """
        Combine extracted features into a single risk score [0, 1].

        Heuristic rules (each produces a partial score in [0, 1]):
        1. Flat MFCCs → TTS / vocoder synthesis
        2. Low delta energy → unnaturally stable prosody
        3. High silence ratio → scripted pauses / trimming
        4. Narrow pitch range → monotone synthetic voice
        5. High ZCR with low variance → digital synthesis artefact
        6. Low spectral variance → narrow-band codec / phone filter
        """
        scores = []

        # ── H1: MFCC variance (low = synthetic) ──────────────────────────────
        # Natural speech: MFCC variance typically > 30
        mfcc_var = f["mfcc_var_mean"]
        h1 = _sigmoid(1.0 / (mfcc_var + 1e-6), k=0.01, x0=50.0)
        scores.append(("mfcc_flat", h1, 0.25))
        logger.debug("H1 mfcc_var=%.2f → risk=%.3f", mfcc_var, h1)

        # ── H2: Delta MFCC energy (low = robotic prosody) ────────────────────
        delta = f["delta_energy"]
        h2 = _sigmoid(1.0 / (delta + 1e-6), k=5.0, x0=2.0)
        scores.append(("delta_energy", h2, 0.20))
        logger.debug("H2 delta_energy=%.4f → risk=%.3f", delta, h2)

        # ── H3: Silence ratio (very high = scripted / clipped audio) ─────────
        silence = f["silence_ratio"]
        # Slight silence is normal; > 40% is suspicious
        h3 = _sigmoid(silence, k=10.0, x0=0.35)
        scores.append(("silence_ratio", h3, 0.15))
        logger.debug("H3 silence=%.3f → risk=%.3f", silence, h3)

        # ── H4: Pitch range (narrow = TTS monotone) ───────────────────────────
        pitch_range = f["pitch_range"]
        # Natural conversation spans > 100 Hz
        h4 = _sigmoid(1.0 / (pitch_range + 1e-6), k=0.02, x0=100.0)
        scores.append(("pitch_range", h4, 0.20))
        logger.debug("H4 pitch_range=%.1f Hz → risk=%.3f", pitch_range, h4)

        # ── H5: ZCR consistency (unnaturally consistent = synthesized) ────────
        zcr_cv = f["zcr_std"] / (f["zcr_mean"] + 1e-6)  # coefficient of variation
        h5 = _sigmoid(1.0 / (zcr_cv + 1e-6), k=5.0, x0=0.3)
        scores.append(("zcr_consistency", h5, 0.10))
        logger.debug("H5 zcr_cv=%.4f → risk=%.3f", zcr_cv, h5)

        # ── H6: Spectral centroid stability (flat = narrow-band synth) ────────
        sc_std = f["spectral_centroid_std"]
        h6 = _sigmoid(1.0 / (sc_std + 1e-6), k=0.001, x0=500.0)
        scores.append(("spectral_stability", h6, 0.10))
        logger.debug("H6 sc_std=%.1f → risk=%.3f", sc_std, h6)

        # ── Weighted average ──────────────────────────────────────────────────
        total_weight = sum(w for _, _, w in scores)
        raw = sum(score * w for _, score, w in scores) / total_weight

        logger.debug(
            "Risk components: %s → raw=%.4f",
            {name: f"{score:.3f}" for name, score, _ in scores},
            raw,
        )
        return raw