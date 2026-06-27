"""
Talk2Mind – Speech Emotion Recognition Module
============================================
Uses librosa for acoustic feature extraction:
    - MFCCs (40 coefficients + deltas)
    - Fundamental frequency (F0/pitch) via YIN algorithm
    - Energy (RMS) contour
    - Zero-crossing rate (ZCR)
    - Spectral centroid, rolloff, bandwidth
    - Chroma features
    - Tempo and beat statistics

Emotion classification uses a prosodic feature rule engine calibrated
on published SER literature (Schuller et al., 2013; El Ayadi et al., 2011).

In production, replace `_classify_from_features()` with:
    - Wav2Vec2 fine-tuned on RAVDESS + CREMA-D + TESS + EMODB
    - Or BiLSTM over MFCC sequences (see scripts/train_speech.py)

Datasets referenced:
    - RAVDESS (Livingstone & Russo, 2018): 7,356 audio/video files
    - CREMA-D (Cao et al., 2014): 7,442 clips, 91 actors
    - TESS (Pichora-Fuller & Dupuis, 2020): 2,800 recordings
    - SAVEE (Haq et al., 2008): 480 utterances (UK English)
    - EMODB (Burkhardt et al., 2005): 800 German utterances
"""

import io
import os
import logging
import tempfile
import subprocess
from typing import Dict, Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ─── Emotion Labels ────────────────────────────────────────────────────────────
EMOTIONS = ["Angry", "Calm", "Disgust", "Fear", "Happy", "Neutral", "Sad"]

# Valence mapping
EMOTION_VALENCE: Dict[str, float] = {
    "Angry":   -0.80,
    "Calm":     0.85,
    "Disgust": -0.60,
    "Fear":    -0.75,
    "Happy":    0.90,
    "Neutral":  0.50,
    "Sad":     -0.70,
}


class SpeechEmotionRecognizer:
    """
    Speech Emotion Recognition pipeline.

    Stage 1 – Pre-processing : Convert to 16kHz mono WAV, denoise
    Stage 2 – Feature extraction: librosa → MFCCs, pitch, energy, spectral
    Stage 3 – Classification : Prosodic rule engine → softmax logits
    """

    def __init__(self):
        self._librosa_available = False
        self._try_import_librosa()

    def _try_import_librosa(self) -> None:
        try:
            import librosa  # noqa: F401
            self._librosa_available = True
            logger.info("librosa initialised successfully.")
        except ImportError:
            logger.warning(
                "librosa not installed – acoustic feature extraction degraded. "
                "Run `pip install librosa soundfile` for full functionality."
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def predict(self, audio_path: str) -> Dict[str, Any]:
        """
        Analyse an audio file and return emotion probabilities.

        Args:
            audio_path: Path to WAV/WebM/MP3 audio file.

        Returns:
            {
                "success":       bool,
                "emotion":       str,
                "probabilities": {str: float},
                "confidence":    float,
                "features":      dict,  # Extracted acoustic features (for XAI)
                "duration_secs": float,
            }
        """
        try:
            wav_path = self._ensure_wav(audio_path)
            if wav_path is None:
                return self._failure_result("Could not decode audio file.")

            if self._librosa_available:
                features = self._extract_features_librosa(wav_path)
            else:
                features = self._extract_features_scipy(wav_path)

            if features is None:
                return self._failure_result("Feature extraction failed.")

            probs = self._classify_from_features(features)
            dominant = max(probs, key=probs.get)
            # Confidence = max probability weighted by feature quality score
            quality_weight = min(1.0, features.get("duration", 1.0) / 3.0)
            confidence = float(max(probs.values()) * quality_weight)

            # Clean up temp file if created
            if wav_path != audio_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except OSError:
                    pass

            return {
                "success": True,
                "emotion": dominant,
                "probabilities": probs,
                "confidence": round(confidence, 4),
                "features": {
                    "mean_pitch_hz":    round(features.get("mean_pitch", 0.0), 2),
                    "pitch_variability": round(features.get("pitch_std", 0.0), 2),
                    "mean_energy_db":   round(features.get("mean_energy_db", 0.0), 2),
                    "speech_rate_bpm":  round(features.get("tempo", 0.0), 1),
                    "mfcc_mean":        [round(v, 3) for v in features.get("mfcc_means", [])[:13]],
                    "spectral_centroid": round(features.get("spectral_centroid", 0.0), 1),
                    "zcr":              round(features.get("zcr", 0.0), 5),
                    "duration":         round(features.get("duration", 0.0), 2),
                },
            }

        except Exception as exc:
            logger.error(f"Speech analysis error: {exc}", exc_info=True)
            return self._failure_result(f"Unexpected error: {str(exc)}")

    # ──────────────────────────────────────────────────────────────────────────
    # Audio preprocessing
    # ──────────────────────────────────────────────────────────────────────────

    def _ensure_wav(self, path: str) -> Optional[str]:
        """Convert audio to 16kHz mono WAV using ffmpeg if needed."""
        if not os.path.exists(path):
            logger.error(f"Audio file not found: {path}")
            return None

        ext = os.path.splitext(path)[1].lower()
        if ext == ".wav":
            return path  # Already WAV

        # Attempt ffmpeg conversion
        try:
            out_path = path.replace(ext, "_converted.wav")
            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", path,
                    "-ar", "16000", "-ac", "1",
                    "-f", "wav", out_path,
                ],
                capture_output=True, timeout=30,
            )
            if result.returncode == 0 and os.path.exists(out_path):
                return out_path
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # If ffmpeg unavailable, try reading as-is (librosa handles many formats)
        return path

    # ──────────────────────────────────────────────────────────────────────────
    # Feature extraction (librosa)
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_features_librosa(self, wav_path: str) -> Optional[Dict]:
        """Extract a comprehensive acoustic feature set using librosa."""
        try:
            import librosa
            import librosa.feature as lf
            import soundfile as sf

            # Load at 16kHz (force mono)
            try:
                y, sr = librosa.load(wav_path, sr=16000, mono=True)
            except Exception:
                y, sr = sf.read(wav_path, always_2d=False)
                if y.ndim > 1:
                    y = y.mean(axis=1)
                y = librosa.resample(y.astype(np.float32), orig_sr=sr, target_sr=16000)
                sr = 16000

            duration = len(y) / sr
            if duration < 0.3:
                logger.warning("Audio too short for reliable analysis.")
                return {"duration": duration, **self._default_features()}

            # ── MFCCs ────────────────────────────────────────────────────────
            mfccs = lf.mfcc(y=y, sr=sr, n_mfcc=40)
            mfcc_means = mfccs.mean(axis=1).tolist()
            mfcc_stds = mfccs.std(axis=1).tolist()
            delta_mfcc = librosa.feature.delta(mfccs)
            delta_means = delta_mfcc.mean(axis=1).tolist()

            # ── Pitch (F0) via YIN ───────────────────────────────────────────
            f0 = librosa.yin(y, fmin=50, fmax=500, sr=sr)
            voiced_f0 = f0[f0 > 60]  # Filter unvoiced frames
            mean_pitch = float(np.mean(voiced_f0)) if len(voiced_f0) > 0 else 0.0
            pitch_std = float(np.std(voiced_f0)) if len(voiced_f0) > 0 else 0.0
            voicing_ratio = len(voiced_f0) / (len(f0) + 1e-6)

            # ── Energy / RMS ─────────────────────────────────────────────────
            rms = lf.rms(y=y)[0]
            mean_rms = float(np.mean(rms))
            mean_energy_db = float(librosa.amplitude_to_db(
                np.array([mean_rms + 1e-9])
            )[0])
            energy_std_db = float(
                librosa.amplitude_to_db(np.array([np.std(rms) + 1e-9]))[0]
            )

            # ── Spectral features ─────────────────────────────────────────────
            spectral_centroid = float(
                lf.spectral_centroid(y=y, sr=sr).mean()
            )
            spectral_rolloff = float(
                lf.spectral_rolloff(y=y, sr=sr, roll_percent=0.85).mean()
            )
            spectral_bandwidth = float(
                lf.spectral_bandwidth(y=y, sr=sr).mean()
            )
            spectral_contrast = lf.spectral_contrast(y=y, sr=sr).mean(axis=1).tolist()

            # ── ZCR ──────────────────────────────────────────────────────────
            zcr = float(lf.zero_crossing_rate(y)[0].mean())

            # ── Chroma ───────────────────────────────────────────────────────
            chroma = lf.chroma_stft(y=y, sr=sr).mean(axis=1).tolist()

            # ── Tempo ─────────────────────────────────────────────────────────
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            tempo = float(tempo) if not isinstance(tempo, np.ndarray) else float(tempo[0])

            return {
                "duration":          duration,
                "mfcc_means":        mfcc_means,
                "mfcc_stds":         mfcc_stds,
                "delta_mfcc_means":  delta_means,
                "mean_pitch":        mean_pitch,
                "pitch_std":         pitch_std,
                "voicing_ratio":     voicing_ratio,
                "mean_energy_db":    mean_energy_db,
                "energy_std_db":     energy_std_db,
                "spectral_centroid": spectral_centroid,
                "spectral_rolloff":  spectral_rolloff,
                "spectral_bandwidth": spectral_bandwidth,
                "spectral_contrast": spectral_contrast,
                "zcr":               zcr,
                "chroma":            chroma,
                "tempo":             tempo,
            }

        except Exception as exc:
            logger.error(f"librosa feature extraction failed: {exc}", exc_info=True)
            return None

    def _extract_features_scipy(self, wav_path: str) -> Optional[Dict]:
        """Minimal feature extraction using only scipy (fallback)."""
        try:
            import wave, struct
            with wave.open(wav_path, "rb") as wf:
                nchannels = wf.getnchannels()
                sr = wf.getframerate()
                nframes = wf.getnframes()
                raw = wf.readframes(nframes)
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                if nchannels > 1:
                    samples = samples.reshape(-1, nchannels).mean(axis=1)

            duration = len(samples) / sr
            zcr = float(np.mean(np.abs(np.diff(np.sign(samples)))) / 2.0)
            rms = float(np.sqrt(np.mean(samples ** 2)))
            mean_energy_db = 20.0 * np.log10(rms + 1e-9)

            return {
                "duration": duration,
                "mfcc_means": [0.0] * 40,
                "mfcc_stds": [0.0] * 40,
                "delta_mfcc_means": [0.0] * 40,
                "mean_pitch": 150.0,
                "pitch_std": 30.0,
                "voicing_ratio": 0.5,
                "mean_energy_db": float(mean_energy_db),
                "energy_std_db": 0.0,
                "spectral_centroid": 2000.0,
                "spectral_rolloff": 3500.0,
                "spectral_bandwidth": 1500.0,
                "spectral_contrast": [0.0] * 7,
                "zcr": zcr,
                "chroma": [0.0] * 12,
                "tempo": 100.0,
            }
        except Exception as exc:
            logger.error(f"scipy feature extraction failed: {exc}")
            return None

    @staticmethod
    def _default_features() -> Dict:
        return {
            "mfcc_means": [0.0] * 40, "mfcc_stds": [0.0] * 40,
            "delta_mfcc_means": [0.0] * 40,
            "mean_pitch": 150.0, "pitch_std": 30.0, "voicing_ratio": 0.5,
            "mean_energy_db": -30.0, "energy_std_db": 5.0,
            "spectral_centroid": 2000.0, "spectral_rolloff": 3500.0,
            "spectral_bandwidth": 1500.0, "spectral_contrast": [0.0] * 7,
            "zcr": 0.05, "chroma": [0.0] * 12, "tempo": 100.0,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Prosodic rule-based classifier
    # ──────────────────────────────────────────────────────────────────────────

    def _classify_from_features(self, features: Dict) -> Dict[str, float]:
        """
        Map acoustic features → emotion logits using published prosodic correlates.

        Key literature:
        - Angry:   High energy, high pitch variance, high ZCR, fast tempo
        - Happy:   High pitch mean, high energy, fast tempo, high spectral centroid
        - Sad:     Low energy, low pitch, slow tempo, low spectral centroid
        - Fear:    High pitch, high variance, high ZCR, breathy voice (low energy)
        - Calm:    Low-mid energy, stable pitch, slow tempo
        - Disgust: Mid pitch, low energy, low ZCR, nasal spectral shape
        - Neutral: Near-mean values on all features
        """
        p = features.get("mean_pitch", 150.0)
        p_std = features.get("pitch_std", 30.0)
        e_db = features.get("mean_energy_db", -30.0)
        e_std = features.get("energy_std_db", 5.0)
        tempo = features.get("tempo", 100.0)
        zcr = features.get("zcr", 0.05)
        sc = features.get("spectral_centroid", 2000.0)
        vr = features.get("voicing_ratio", 0.5)

        # Normalised feature helpers (0–1 range relative to typical speech)
        pitch_high = _sigmoid((p - 200.0) / 60.0)         # >200 Hz = high
        pitch_low = _sigmoid((150.0 - p) / 40.0)          # <150 Hz = low
        pitch_variable = _sigmoid((p_std - 40.0) / 20.0)  # std>40 = variable
        energy_high = _sigmoid((e_db + 20.0) / 10.0)      # >-20 dB = loud
        energy_low = _sigmoid((-40.0 - e_db) / 10.0)      # <-40 dB = quiet
        tempo_fast = _sigmoid((tempo - 120.0) / 30.0)
        tempo_slow = _sigmoid((80.0 - tempo) / 20.0)
        zcr_high = _sigmoid((zcr - 0.08) / 0.03)
        sc_high = _sigmoid((sc - 2500.0) / 500.0)
        voiced_high = _sigmoid((vr - 0.55) / 0.15)

        logits = {
            "Angry":   energy_high * 2.5 + pitch_variable * 1.5 + zcr_high * 1.5 + tempo_fast * 1.0,
            "Happy":   pitch_high * 2.0 + energy_high * 1.5 + tempo_fast * 1.5 + sc_high * 1.0,
            "Sad":     energy_low * 2.5 + pitch_low * 2.0 + tempo_slow * 1.5 + (1.0 - zcr_high) * 0.5,
            "Fear":    pitch_high * 1.5 + pitch_variable * 2.0 + zcr_high * 1.5 + (1.0 - energy_high) * 1.0,
            "Calm":    voiced_high * 1.5 + (1.0 - pitch_variable) * 1.5 + tempo_slow * 1.0 + (1.0 - energy_high) * 1.0,
            "Disgust": (1.0 - voiced_high) * 1.5 + energy_low * 1.0 + (1.0 - zcr_high) * 1.0 + 0.5,
            "Neutral": 1.5,  # Prior
        }
        return _softmax(logits)

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _failure_result(reason: str) -> Dict[str, Any]:
        return {
            "success": False,
            "emotion": "Neutral",
            "probabilities": {e: 1.0 / len(EMOTIONS) for e in EMOTIONS},
            "confidence": 0.0,
            "features": {},
            "duration_secs": 0.0,
            "reason": reason,
        }


# ─── Math helpers ─────────────────────────────────────────────────────────────

def _sigmoid(x: float) -> float:
    import math
    return 1.0 / (1.0 + math.exp(-max(-50.0, min(50.0, x))))


def _softmax(logits: Dict[str, float]) -> Dict[str, float]:
    vals = np.array(list(logits.values()), dtype=np.float64)
    vals -= vals.max()
    exp_vals = np.exp(vals)
    probs = exp_vals / exp_vals.sum()
    return {k: round(float(v), 6) for k, v in zip(logits.keys(), probs)}


# ─── Singleton instance ───────────────────────────────────────────────────────
speech_recognizer = SpeechEmotionRecognizer()
