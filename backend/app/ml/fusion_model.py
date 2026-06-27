from typing import Dict, Any, Optional
import os
import pickle
import numpy as np
from ..config import settings

class MultimodalFusionModel:
    def __init__(self):
        self.model_path = os.path.join(settings.MODEL_DIR, "fusion_model.pkl")
        self.model = None
        self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
            except Exception as e:
                print(f"Error loading fusion model: {e}. Using weighted late fusion rules.")

    def fuse(
        self,
        questionnaire_results: Dict[str, Any],
        facial_results: Dict[str, Any],
        speech_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combines scores from the questionnaire, facial analysis, and speech analysis.
        Generates:
        - Fused Mental Well-Being Score (0-100)
        - Confidence Level (0.0 to 1.0)
        - Classification Label
        """
        q_score = questionnaire_results["score"]
        
        # Determine presence and quality of visual/audio inputs
        face_active = facial_results.get("detected", False)
        speech_active = speech_results.get("success", False)
        
        # Extract normalized valence/wellbeing indicators from emotions
        # Happy, Surprise, Calm, Neutral are positive wellbeing markers (high valence).
        # Angry, Sad, Fear, Disgust are negative wellbeing markers (low valence).
        
        # Visual wellness score mapping
        if face_active:
            probs = facial_results["probabilities"]
            positive_face = probs.get("Happy", 0.0) + probs.get("Surprise", 0.0) * 0.5 + probs.get("Neutral", 0.0) * 0.8
            negative_face = probs.get("Angry", 0.0) + probs.get("Sad", 0.0) + probs.get("Fear", 0.0) + probs.get("Disgust", 0.0)
            
            # Score from 0 to 100 based on positive vs negative expressions
            face_score = (positive_face / (positive_face + negative_face + 1e-9)) * 100.0
            face_conf = facial_results.get("confidence", 0.5)
        else:
            face_score = q_score
            face_conf = 0.0
            
        # Audio wellness score mapping
        if speech_active:
            probs = speech_results["probabilities"]
            positive_speech = probs.get("Happy", 0.0) + probs.get("Calm", 0.0) * 0.9 + probs.get("Neutral", 0.0) * 0.8
            negative_speech = probs.get("Angry", 0.0) + probs.get("Sad", 0.0) + probs.get("Fear", 0.0) + probs.get("Disgust", 0.0)
            
            speech_score = (positive_speech / (positive_speech + negative_speech + 1e-9)) * 100.0
            speech_conf = speech_results.get("confidence", 0.5)
        else:
            speech_score = q_score
            speech_conf = 0.0

        # Late fusion logic
        if face_active and speech_active:
            # All modalities present
            # Weight distribution: Questionnaire (50%), Face (25%), Speech (25%)
            fused_score = 0.50 * q_score + 0.25 * face_score + 0.25 * speech_score
            base_confidence = 0.90
            # Adjust confidence based on model accuracy outputs
            confidence = base_confidence * (0.6 + 0.2 * face_conf + 0.2 * speech_conf)
        elif face_active:
            # Face + Questionnaire
            fused_score = 0.65 * q_score + 0.35 * face_score
            base_confidence = 0.75
            confidence = base_confidence * (0.7 + 0.3 * face_conf)
        elif speech_active:
            # Speech + Questionnaire
            fused_score = 0.65 * q_score + 0.35 * speech_score
            base_confidence = 0.75
            confidence = base_confidence * (0.7 + 0.3 * speech_conf)
        else:
            # Questionnaire only
            fused_score = q_score
            confidence = 0.60
            
        # Safety clipping
        fused_score = max(0.0, min(100.0, float(fused_score)))
        confidence = max(0.0, min(1.0, float(confidence)))
        
        # Clinical Risk Classification based on scale cutoffs and final score
        phq_clinical = questionnaire_results["phq9"]["clinical_cut_off"]
        gad_clinical = questionnaire_results["gad7"]["clinical_cut_off"]
        
        if phq_clinical and fused_score < 60:
            classification = "Depression Risk"
        elif gad_clinical and fused_score < 60:
            classification = "Anxiety Risk"
        elif fused_score >= 80:
            classification = "Healthy"
        elif fused_score >= 65:
            classification = "Mild Stress"
        elif fused_score >= 50:
            classification = "Moderate Stress"
        else:
            classification = "High Stress"

        return {
            "facial_score": float(face_score) if face_active else None,
            "speech_score": float(speech_score) if speech_active else None,
            "questionnaire_score": float(q_score),
            "fused_score": fused_score,
            "confidence": confidence,
            "classification": classification
        }

fusion_model = MultimodalFusionModel()
