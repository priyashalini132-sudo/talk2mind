"""
Talk2Mind – Facial Emotion Recognition Module
=============================================
Uses OpenCV for face detection and MediaPipe for landmark extraction.
Emotion probabilities are derived from geometric facial feature analysis
(Action Unit mapping), providing a scientifically-grounded heuristic model.

In production, replace `_heuristic_emotion_from_landmarks()` with a
fine-tuned EfficientNet-B0 or ResNet-50 model trained on FER2013/AffectNet.
See: scripts/train_facial.py for the full training pipeline.

Datasets referenced:
    - FER2013 (Goodfellow et al., 2013): 35,887 labeled facial images
    - AffectNet (Mollahosseini et al., 2017): 450,000+ images

Model Architecture (production):
    EfficientNet-B0 → Global Average Pooling → Dense(256, ReLU) → Dense(7, Softmax)
    Input: 224x224 RGB face crop
    Output: 7-class emotion probabilities
"""

import io
import math
import logging
from typing import Dict, Any, Optional, List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ─── Emotion Labels ────────────────────────────────────────────────────────────
EMOTIONS = ["Angry", "Disgust", "Fear", "Happy", "Neutral", "Sad", "Surprise"]

# Valence mapping for each emotion (used in wellness scoring)
EMOTION_VALENCE: Dict[str, float] = {
    "Angry":    -0.80,
    "Disgust":  -0.65,
    "Fear":     -0.75,
    "Happy":     0.95,
    "Neutral":   0.50,
    "Sad":      -0.70,
    "Surprise":  0.30,  # Surprise is ambiguous; slight positive bias
}


class FacialEmotionRecognizer:
    """
    Multimodal Facial Emotion Recognition pipeline.
    
    Stage 1 – Detection:  OpenCV Haar Cascade / DNN face detector
    Stage 2 – Landmarks:  MediaPipe FaceMesh (468 landmarks)
    Stage 3 – Inference:  Landmark-geometry AU heuristics → emotion softmax
    
    In production Stage 3 is replaced by a pre-trained CNN (see scripts/).
    """

    def __init__(self):
        self._face_cascade: Optional[cv2.CascadeClassifier] = None
        self._mediapipe_available = False
        self._mp_face_mesh = None
        self._mp_face_detection = None
        self._initialize_detectors()

    # ──────────────────────────────────────────────────────────────────────────
    # Initialization
    # ──────────────────────────────────────────────────────────────────────────

    def _initialize_detectors(self) -> None:
        """Load OpenCV and optionally MediaPipe detectors."""
        # OpenCV Haar Cascade (reliable fallback)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._face_cascade = cv2.CascadeClassifier(cascade_path)
        if self._face_cascade.empty():
            logger.warning("Haar cascade failed to load – face detection may be degraded.")
            self._face_cascade = None

        # MediaPipe FaceMesh (preferred for landmark extraction)
        try:
            import mediapipe as mp  # type: ignore
            self._mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
            )
            self._mp_face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=1,
                min_detection_confidence=0.5,
            )
            self._mediapipe_available = True
            logger.info("MediaPipe FaceMesh initialised successfully.")
        except ImportError:
            logger.warning(
                "MediaPipe not installed – landmark-based analysis disabled. "
                "Run `pip install mediapipe` for enhanced accuracy."
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def predict(self, frame_bytes: bytes) -> Dict[str, Any]:
        """
        Analyse a JPEG/PNG image frame and return emotion probabilities.

        Args:
            frame_bytes: Raw bytes of the image (JPEG or PNG).

        Returns:
            {
                "detected":      bool,
                "emotion":       str,          # Dominant emotion label
                "probabilities": {str: float}, # Softmax distribution over 7 classes
                "confidence":    float,        # Detector confidence 0–1
                "face_box":      Optional[dict], # {x, y, w, h} in pixel coords
                "quality":       str,          # "good" | "low_light" | "blurry"
                "landmarks":     Optional[List], # [x,y] pairs (MediaPipe)
            }
        """
        try:
            img_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if frame is None:
                return self._no_face_result("Failed to decode image bytes")

            quality = self._assess_quality(frame)

            # Try MediaPipe first, then fall back to Haar
            face_box, landmarks, mp_confidence = self._detect_with_mediapipe(frame)
            if face_box is None:
                face_box, haar_confidence = self._detect_with_haar(frame)
                landmarks = None
                detector_conf = haar_confidence
            else:
                detector_conf = mp_confidence

            if face_box is None:
                return self._no_face_result("No face detected in frame")

            # Crop face ROI for analysis
            x, y, w, h = face_box
            face_roi = frame[y : y + h, x : x + w]

            # Compute emotion probabilities
            if landmarks is not None and self._mediapipe_available:
                probs = self._emotion_from_landmarks(landmarks, frame.shape)
            else:
                probs = self._emotion_from_roi_features(face_roi)

            dominant_emotion = max(probs, key=probs.get)
            confidence = float(detector_conf * max(probs.values()))

            return {
                "detected": True,
                "emotion": dominant_emotion,
                "probabilities": probs,
                "confidence": round(confidence, 4),
                "face_box": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
                "quality": quality,
                "landmarks": None,  # Not serialised (too large)
            }

        except Exception as exc:
            logger.error(f"Facial analysis error: {exc}", exc_info=True)
            return self._no_face_result(f"Processing error: {str(exc)}")

    # ──────────────────────────────────────────────────────────────────────────
    # Detection backends
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_with_mediapipe(
        self, frame: np.ndarray
    ) -> Tuple[Optional[Tuple], Optional[List], float]:
        """Detect face using MediaPipe Detection model. Returns (box, landmarks, conf)."""
        if not self._mediapipe_available:
            return None, None, 0.0
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame.shape[:2]

            # Face detection for bounding box
            det_results = self._mp_face_detection.process(rgb)
            if not det_results.detections:
                return None, None, 0.0

            det = det_results.detections[0]
            confidence = float(det.score[0])
            bbox = det.location_data.relative_bounding_box
            x = max(0, int(bbox.xmin * w))
            y = max(0, int(bbox.ymin * h))
            bw = min(int(bbox.width * w), w - x)
            bh = min(int(bbox.height * h), h - y)

            # Landmark extraction
            mesh_results = self._mp_face_mesh.process(rgb)
            landmarks = None
            if mesh_results.multi_face_landmarks:
                raw = mesh_results.multi_face_landmarks[0].landmark
                landmarks = [(lm.x * w, lm.y * h, lm.z) for lm in raw]

            return (x, y, bw, bh), landmarks, confidence
        except Exception as exc:
            logger.debug(f"MediaPipe detection failed: {exc}")
            return None, None, 0.0

    def _detect_with_haar(
        self, frame: np.ndarray
    ) -> Tuple[Optional[Tuple], float]:
        """Detect face using OpenCV Haar cascade. Returns (box, conf)."""
        if self._face_cascade is None:
            return None, 0.0
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            faces = self._face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )
            if len(faces) == 0:
                return None, 0.0
            # Pick largest face
            areas = [w * h for (_, _, w, h) in faces]
            best_idx = int(np.argmax(areas))
            x, y, w, h = faces[best_idx]
            # Confidence approximation based on face size relative to frame
            frame_area = frame.shape[0] * frame.shape[1]
            size_conf = min(1.0, (w * h) / (frame_area * 0.15))
            return (x, y, w, h), max(0.55, size_conf)
        except Exception as exc:
            logger.debug(f"Haar detection failed: {exc}")
            return None, 0.0

    # ──────────────────────────────────────────────────────────────────────────
    # Emotion inference
    # ──────────────────────────────────────────────────────────────────────────

    def _emotion_from_landmarks(
        self, landmarks: List[Tuple], frame_shape: Tuple
    ) -> Dict[str, float]:
        """
        Derive emotion logits from geometric facial Action Units (AUs).

        Key landmark indices (MediaPipe FaceMesh 468-point model):
            Lip corners:  61 (left), 291 (right)
            Lip top:      0 (centre top)
            Lip bottom:   17 (centre bottom)
            Left brow:    105, 107
            Right brow:   334, 336
            Left eye:     159, 145  (top/bottom)
            Right eye:    386, 374
            Nose tip:     1
            Cheeks:       50 (left), 280 (right)
        """
        try:
            lm = landmarks  # alias

            def dist(i: int, j: int) -> float:
                return math.sqrt(
                    (lm[i][0] - lm[j][0]) ** 2 + (lm[i][1] - lm[j][1]) ** 2
                )

            # ── Mouth aspect ratio (smile / open mouth) ──────────────────────
            mouth_width = dist(61, 291)
            mouth_height = dist(0, 17)
            mar = mouth_height / (mouth_width + 1e-6)

            # ── Lip corner Y displacement (up = smile, down = frown) ─────────
            nose_y = lm[1][1]
            left_corner_y = lm[61][1]
            right_corner_y = lm[291][1]
            avg_corner_y = (left_corner_y + right_corner_y) / 2
            corner_rise = nose_y - avg_corner_y  # positive = corners above nose (smile)

            # ── Brow raise (AU1/2 inner/outer brow raiser) ───────────────────
            left_brow_y = (lm[105][1] + lm[107][1]) / 2
            right_brow_y = (lm[334][1] + lm[336][1]) / 2
            left_eye_y = (lm[159][1] + lm[145][1]) / 2
            right_eye_y = (lm[386][1] + lm[374][1]) / 2
            brow_eye_dist = (
                (left_eye_y - left_brow_y) + (right_eye_y - right_brow_y)
            ) / 2
            # Normalise by inter-ocular distance
            iod = dist(33, 263)  # inner eye corners
            brow_raise_norm = brow_eye_dist / (iod + 1e-6)

            # ── Eye openness (AU5 upper lid raiser) ──────────────────────────
            left_eye_open = dist(159, 145) / (iod + 1e-6)
            right_eye_open = dist(386, 374) / (iod + 1e-6)
            avg_eye_open = (left_eye_open + right_eye_open) / 2

            # ── Brow furrow (AU4 corrugator) ─────────────────────────────────
            inner_brow_dist = dist(107, 336)  # inner brow landmarks
            brow_furrow_norm = inner_brow_dist / (iod + 1e-6)

            # ── AU to emotion logit mapping ───────────────────────────────────
            logits = {
                "Happy":    _sigmoid(corner_rise / (iod * 0.15 + 1e-6)) * 3.0
                            + _sigmoid(-mar + 0.15) * 1.5,
                "Sad":      _sigmoid(-corner_rise / (iod * 0.12 + 1e-6)) * 2.5
                            + _sigmoid(0.6 - brow_raise_norm) * 1.0,
                "Surprise": _sigmoid(mar - 0.2) * 2.0
                            + _sigmoid(brow_raise_norm - 0.8) * 2.0
                            + _sigmoid(avg_eye_open - 0.18) * 1.0,
                "Fear":     _sigmoid(mar - 0.15) * 1.5
                            + _sigmoid(brow_raise_norm - 0.75) * 1.5
                            + _sigmoid(-corner_rise / (iod * 0.2 + 1e-6)) * 1.0,
                "Angry":    _sigmoid(0.75 - brow_furrow_norm) * 2.5
                            + _sigmoid(-corner_rise / (iod * 0.1 + 1e-6)) * 1.0,
                "Disgust":  _sigmoid(0.72 - brow_furrow_norm) * 1.5
                            + _sigmoid(-mar + 0.05) * 1.0,
                "Neutral":  1.5,  # prior for neutral (most common expression)
            }

            return _softmax(logits)

        except (IndexError, ZeroDivisionError) as exc:
            logger.debug(f"Landmark-based inference failed: {exc}")
            return self._emotion_from_roi_features(None)

    def _emotion_from_roi_features(
        self, face_roi: Optional[np.ndarray]
    ) -> Dict[str, float]:
        """
        Fallback: compute emotion probabilities from image-level statistics
        when landmark extraction is unavailable.
        """
        if face_roi is None or face_roi.size == 0:
            return _softmax({e: 1.0 for e in EMOTIONS})

        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Pixel intensity statistics
        mean_val = float(np.mean(gray))
        std_val = float(np.std(gray))

        # Gradient (edge energy → muscular tension proxy)
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_energy = float(np.mean(np.sqrt(gx ** 2 + gy ** 2)))

        # Upper/lower face brightness ratio (brow furrow → darker upper face)
        upper_mean = float(np.mean(gray[: h // 2, :]))
        lower_mean = float(np.mean(gray[h // 2 :, :]))
        ul_ratio = upper_mean / (lower_mean + 1e-6)

        logits = {
            "Neutral":  2.0,
            "Happy":    _sigmoid((lower_mean - upper_mean) / 20.0) * 2.0,
            "Sad":      _sigmoid((upper_mean - lower_mean) / 20.0) * 1.5,
            "Angry":    _sigmoid((edge_energy - 15.0) / 10.0) * 1.5,
            "Disgust":  _sigmoid((edge_energy - 20.0) / 10.0) * 1.0,
            "Fear":     _sigmoid((std_val - 40.0) / 20.0) * 1.5,
            "Surprise": _sigmoid((std_val - 50.0) / 20.0) * 1.0,
        }
        return _softmax(logits)

    # ──────────────────────────────────────────────────────────────────────────
    # Image quality assessment
    # ──────────────────────────────────────────────────────────────────────────

    def _assess_quality(self, frame: np.ndarray) -> str:
        """Return 'good', 'blurry', or 'low_light'."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        if brightness < 40:
            return "low_light"
        if laplacian_var < 80:
            return "blurry"
        return "good"

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _no_face_result(reason: str) -> Dict[str, Any]:
        return {
            "detected": False,
            "emotion": "Neutral",
            "probabilities": {e: 1.0 / len(EMOTIONS) for e in EMOTIONS},
            "confidence": 0.0,
            "face_box": None,
            "quality": "unknown",
            "landmarks": None,
            "reason": reason,
        }


# ─── Math helpers ─────────────────────────────────────────────────────────────

def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _softmax(logits: Dict[str, float]) -> Dict[str, float]:
    """Numerically-stable softmax over a dict of logits."""
    vals = np.array(list(logits.values()), dtype=np.float64)
    vals -= vals.max()
    exp_vals = np.exp(vals)
    probs = exp_vals / exp_vals.sum()
    return {k: round(float(v), 6) for k, v in zip(logits.keys(), probs)}


# ─── Singleton instance ───────────────────────────────────────────────────────
facial_recognizer = FacialEmotionRecognizer()
