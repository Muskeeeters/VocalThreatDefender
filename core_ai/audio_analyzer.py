"""
core_ai/audio_analyzer.py
==========================
MODULE 1 — Audio Risk Analyzer
"""

import logging
import warnings
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=UserWarning, module="librosa")
warnings.filterwarnings("ignore", category=FutureWarning, module="librosa")

TARGET_SR = 16_000
N_MFCC = 40
HOP_LENGTH = 512
N_FFT = 1024

def _sigmoid(x: float, k: float = 8.0, x0: float = 0.5) -> float:
    return 1.0 / (1.0 + np.exp(-k * (x - x0)))

class AudioRiskAnalyzer:
    def __init__(self):
        logger.info("AudioRiskAnalyzer initialised (target_sr=%d Hz)", TARGET_SR)

    def analyze(self, file_path: str) -> dict:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        try:
            import librosa
        except ImportError as exc:
            raise ImportError("librosa is required. Install with: pip install librosa") from exc

        # ── Load & resample ───────────────────────────────────────────────────
        try:
            logger.info("    [~] Resampling audio stream to 16,000 Hz telephony standard...")
            audio, sr = librosa.load(str(path), sr=TARGET_SR, mono=True)
        except Exception as exc:
            raise ValueError(f"Could not load audio file: {exc}") from exc

        duration = len(audio) / sr
        logger.info(f"    [~] Stream successfully captured: {duration:.2f} seconds.")

        if duration < 0.5:
            logger.warning("    [!] Audio too short — returning neutral score")
            return {"audio_risk": 0.3}

        # ── Feature extraction ────────────────────────────────────────────────
        logger.info("    [~] Commencing Deepfake acoustic feature extraction (MFCCs, Spectral Centroids, Pitch)...")
        features = self._extract_features(audio, sr, librosa)

        # ── Heuristic scoring ─────────────────────────────────────────────────
        logger.info("    [+] Feature extraction successful! Evaluating heuristic threat rules...")
        risk_score = self._compute_risk(features, duration)

        return {"audio_risk": float(np.clip(risk_score, 0.0, 1.0))}

    def _extract_features(self, audio: np.ndarray, sr: int, librosa) -> dict:
        features = {}
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC, hop_length=HOP_LENGTH, n_fft=N_FFT)
        features["mfcc"] = mfcc
        features["mfcc_mean"] = np.mean(mfcc, axis=1)
        features["mfcc_std"] = np.std(mfcc, axis=1)
        features["mfcc_var_mean"] = float(np.mean(np.var(mfcc, axis=1)))

        delta_mfcc = librosa.feature.delta(mfcc)
        features["delta_energy"] = float(np.mean(np.abs(delta_mfcc)))

        spec_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr, hop_length=HOP_LENGTH)
        features["spectral_centroid_std"] = float(np.std(spec_centroid))

        spec_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr, hop_length=HOP_LENGTH)
        features["spectral_rolloff_std"] = float(np.std(spec_rolloff))

        zcr = librosa.feature.zero_crossing_rate(audio, hop_length=HOP_LENGTH)
        features["zcr_mean"] = float(np.mean(zcr))
        features["zcr_std"] = float(np.std(zcr))

        rms = librosa.feature.rms(y=audio, hop_length=HOP_LENGTH)[0]
        silence_threshold = 0.01 * np.max(rms) if np.max(rms) > 0 else 0.0
        features["silence_ratio"] = float(np.mean(rms < silence_threshold))
        features["rms_std"] = float(np.std(rms))

        try:
            f0, voiced_flag, _ = librosa.pyin(audio, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr)
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
        scores = []
        logger.info("    [~] Analyzing MFCC variance for TTS vocoder signatures...")
        h1 = _sigmoid(1.0 / (f["mfcc_var_mean"] + 1e-6), k=0.01, x0=50.0)
        scores.append(("mfcc_flat", h1, 0.25))

        logger.info("    [~] Evaluating delta energy prosody algorithms...")
        h2 = _sigmoid(1.0 / (f["delta_energy"] + 1e-6), k=5.0, x0=2.0)
        scores.append(("delta_energy", h2, 0.20))

        logger.info("    [~] Cross-referencing pitch range against human baselines...")
        h3 = _sigmoid(f["silence_ratio"], k=10.0, x0=0.35)
        scores.append(("silence_ratio", h3, 0.15))

        h4 = _sigmoid(1.0 / (f["pitch_range"] + 1e-6), k=0.02, x0=100.0)
        scores.append(("pitch_range", h4, 0.20))

        h5 = _sigmoid(1.0 / ((f["zcr_std"] / (f["zcr_mean"] + 1e-6)) + 1e-6), k=5.0, x0=0.3)
        scores.append(("zcr_consistency", h5, 0.10))

        h6 = _sigmoid(1.0 / (f["spectral_centroid_std"] + 1e-6), k=0.001, x0=500.0)
        scores.append(("spectral_stability", h6, 0.10))

        total_weight = sum(w for _, _, w in scores)
        raw = sum(score * w for _, score, w in scores) / total_weight
        return raw