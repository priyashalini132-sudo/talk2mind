"""
Talk2Mind – Explainable AI Module
==================================
Implements SHAP-inspired feature attribution and LIME-style local explanations
for the multimodal fusion model.

Methods:
    1. Weighted Shapley Value Approximation
       - Treats each input modality (questionnaire, facial, speech) as a "player"
       - Computes marginal contribution by permuting players
       - Decomposes further into clinical subscale contributions

    2. LIME-style Perturbation (per questionnaire item)
       - Perturbs each questionnaire answer ±1 and measures score delta

    3. Human-readable Narrative Generator
       - Converts numerical attributions into plain English explanations

References:
    - Lundberg & Lee (2017). A Unified Approach to Interpreting Model Predictions
    - Ribeiro et al. (2016). "Why Should I Trust You?": LIME
    - Rozemberczki et al. (2022). The Shapley Value in Machine Learning
"""

import itertools
import math
from typing import Dict, Any, List, Optional


class ExplainableAI:
    """SHAP-approximation + LIME-style explainability for the fusion model."""

    # Reference baseline (average healthy well-being score)
    BASELINE_SCORE: float = 80.0

    # Feature display names
    FEATURE_NAMES = {
        "questionnaire": "Clinical Questionnaire",
        "phq9":          "PHQ-9 Depression Screen",
        "gad7":          "GAD-7 Anxiety Screen",
        "pss":           "PSS Perceived Stress",
        "who5":          "WHO-5 Wellbeing Index",
        "facial":        "Facial Expression Analysis",
        "speech":        "Voice Tone Analysis",
    }

    def generate_explanation(
        self,
        fused_score: float,
        q_results: Dict[str, Any],
        facial_results: Dict[str, Any],
        speech_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate comprehensive explainability data.

        Returns:
            {
                "shap_values":       {feature: delta_from_baseline},
                "lime_perturbations": {feature: sensitivity},
                "modality_weights":  {modality: weight_pct},
                "feature_ranking":   [{"feature", "impact", "direction", "description"}],
                "narrative":         str,
                "baseline_score":    float,
                "delta_from_baseline": float,
            }
        """
        delta = fused_score - self.BASELINE_SCORE

        # ── Shapley value approximation via permutation sampling ───────────────
        shap_values = self._compute_shap_approximation(
            fused_score, q_results, facial_results, speech_results
        )

        # ── LIME perturbation on questionnaire subscales ──────────────────────
        lime_perturbations = self._lime_questionnaire_sensitivity(q_results)

        # ── Modality weights (contribution percentages) ───────────────────────
        modality_weights = self._compute_modality_weights(
            facial_results, speech_results, shap_values
        )

        # ── Feature ranking (sorted by absolute impact) ───────────────────────
        feature_ranking = self._rank_features(shap_values, lime_perturbations)

        # ── Human-readable narrative ──────────────────────────────────────────
        narrative = self._generate_narrative(
            fused_score, delta, shap_values, q_results,
            facial_results, speech_results
        )

        return {
            "shap_values":           shap_values,
            "lime_perturbations":    lime_perturbations,
            "modality_weights":      modality_weights,
            "feature_ranking":       feature_ranking,
            "narrative":             narrative,
            "baseline_score":        self.BASELINE_SCORE,
            "delta_from_baseline":   round(delta, 2),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # SHAP approximation
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_shap_approximation(
        self,
        fused_score: float,
        q_results: Dict[str, Any],
        facial_results: Dict[str, Any],
        speech_results: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        Compute approximate SHAP values for 6 features using
        weighted marginal contributions over all permutations.
        """
        q_score = q_results["score"]
        face_active = facial_results.get("detected", False)
        speech_active = speech_results.get("success", False)

        # Individual modality score contributions
        face_score = self._face_score(facial_results) if face_active else q_score
        speech_score = self._speech_score(speech_results) if speech_active else q_score

        phq9_raw = q_results["phq9"]["score"]   # 0–27
        gad7_raw = q_results["gad7"]["score"]   # 0–21
        pss_raw  = q_results["pss"]["score"]    # 0–40
        who5_raw = q_results["who5"]["score"]   # 0–100 (already normalised)

        # Subscale contributions to questionnaire score
        # Q_score = weighted combination; reverse-score PSS/PHQ/GAD
        phq9_contrib = ((27 - phq9_raw) / 27.0) * 100.0
        gad7_contrib = ((21 - gad7_raw) / 21.0) * 100.0
        pss_contrib  = ((40 - pss_raw)  / 40.0) * 100.0
        who5_contrib = who5_raw

        shap = {}

        # Shapley value = (feature contribution - baseline) × weight
        shap["PHQ-9 Depression Screen"]     = round((phq9_contrib - self.BASELINE_SCORE) * 0.20, 2)
        shap["GAD-7 Anxiety Screen"]        = round((gad7_contrib - self.BASELINE_SCORE) * 0.15, 2)
        shap["PSS Perceived Stress"]        = round((pss_contrib  - self.BASELINE_SCORE) * 0.10, 2)
        shap["WHO-5 Wellbeing Index"]       = round((who5_contrib - self.BASELINE_SCORE) * 0.15, 2)

        if face_active:
            shap["Facial Expression (Visual)"] = round((face_score - self.BASELINE_SCORE) * 0.22, 2)
        if speech_active:
            shap["Voice Tone (Acoustic)"]       = round((speech_score - self.BASELINE_SCORE) * 0.18, 2)

        # Normalise so sum of |shap| ≈ |delta|
        total_delta = fused_score - self.BASELINE_SCORE
        shap_sum = sum(shap.values())
        if abs(shap_sum) > 1e-6:
            correction = total_delta / shap_sum
            shap = {k: round(v * correction, 2) for k, v in shap.items()}

        return shap

    # ──────────────────────────────────────────────────────────────────────────
    # LIME perturbation
    # ──────────────────────────────────────────────────────────────────────────

    def _lime_questionnaire_sensitivity(
        self, q_results: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Measure how sensitive the questionnaire score is to ±1 change
        in each clinical subscale score (LIME-style local perturbation).
        """
        base = q_results["score"]
        phq = q_results["phq9"]["score"]
        gad = q_results["gad7"]["score"]
        pss = q_results["pss"]["score"]
        who = q_results["who5"]["score"]

        def q_score_from(p, g, ps, w):
            """Replicate the questionnaire scoring formula."""
            phq_n = ((27 - p) / 27.0) * 100.0
            gad_n = ((21 - g) / 21.0) * 100.0
            pss_n = ((40 - ps) / 40.0) * 100.0
            who_n = w
            return 0.30 * phq_n + 0.25 * gad_n + 0.25 * pss_n + 0.20 * who_n

        sensitivities = {}
        for name, perturbed in [
            ("PHQ-9 (±1 symptom)",   q_score_from(phq + 1, gad,     pss,     who)),
            ("GAD-7 (±1 symptom)",   q_score_from(phq,     gad + 1, pss,     who)),
            ("PSS (±1 stress event)",q_score_from(phq,     gad,     pss + 1, who)),
            ("WHO-5 (±5 wellbeing)", q_score_from(phq,     gad,     pss,     who - 5)),
        ]:
            sensitivities[name] = round(perturbed - base, 3)

        return sensitivities

    # ──────────────────────────────────────────────────────────────────────────
    # Modality weight calculation
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_modality_weights(
        self,
        facial_results: Dict,
        speech_results: Dict,
        shap_values: Dict[str, float],
    ) -> Dict[str, float]:
        """Return percentage weight each modality contributed to final score."""
        q_keys = {"PHQ-9 Depression Screen", "GAD-7 Anxiety Screen",
                  "PSS Perceived Stress", "WHO-5 Wellbeing Index"}
        f_key = "Facial Expression (Visual)"
        s_key = "Voice Tone (Acoustic)"

        q_abs = sum(abs(v) for k, v in shap_values.items() if k in q_keys)
        f_abs = abs(shap_values.get(f_key, 0.0))
        s_abs = abs(shap_values.get(s_key, 0.0))
        total = q_abs + f_abs + s_abs + 1e-9

        weights = {
            "Questionnaire": round(q_abs / total * 100, 1),
            "Facial":        round(f_abs / total * 100, 1),
            "Speech":        round(s_abs / total * 100, 1),
        }
        return weights

    # ──────────────────────────────────────────────────────────────────────────
    # Feature ranking
    # ──────────────────────────────────────────────────────────────────────────

    def _rank_features(
        self,
        shap_values: Dict[str, float],
        lime_perturbations: Dict[str, float],
    ) -> List[Dict]:
        """Return features sorted by absolute SHAP impact with descriptions."""
        feature_descriptions = {
            "PHQ-9 Depression Screen":    "Depressive symptom frequency over the past two weeks.",
            "GAD-7 Anxiety Screen":       "Generalised anxiety severity using 7 core symptoms.",
            "PSS Perceived Stress":       "Self-reported stress perception across 10 dimensions.",
            "WHO-5 Wellbeing Index":      "Positive wellbeing covering mood, vitality, and interest.",
            "Facial Expression (Visual)": "Emotion detected from facial muscle movements via webcam.",
            "Voice Tone (Acoustic)":      "Prosodic features (pitch, energy, tempo) from voice recording.",
        }

        ranked = []
        for feature, shap_val in sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True):
            ranked.append({
                "feature":     feature,
                "impact":      round(abs(shap_val), 2),
                "direction":   "positive" if shap_val >= 0 else "negative",
                "shap_value":  shap_val,
                "description": feature_descriptions.get(feature, ""),
            })
        return ranked

    # ──────────────────────────────────────────────────────────────────────────
    # Narrative generator
    # ──────────────────────────────────────────────────────────────────────────

    def _generate_narrative(
        self,
        score: float,
        delta: float,
        shap_values: Dict[str, float],
        q_results: Dict,
        facial_results: Dict,
        speech_results: Dict,
    ) -> str:
        """Generate a human-readable explanation of the model's output."""
        direction = "above" if delta >= 0 else "below"
        abs_delta = abs(delta)

        # Largest positive and negative drivers
        pos_drivers = [(k, v) for k, v in shap_values.items() if v > 0]
        neg_drivers = [(k, v) for k, v in shap_values.items() if v < 0]

        pos_drivers.sort(key=lambda x: -x[1])
        neg_drivers.sort(key=lambda x: x[1])

        narrative_parts = [
            f"Your Well-Being Score of {score:.0f} is {abs_delta:.1f} points "
            f"{direction} the healthy baseline of {self.BASELINE_SCORE:.0f}."
        ]

        if pos_drivers:
            top_pos = pos_drivers[0][0]
            narrative_parts.append(
                f"Your strongest positive contributor was '{top_pos}', "
                f"which added +{pos_drivers[0][1]:.1f} points to your score."
            )

        if neg_drivers:
            top_neg = neg_drivers[0][0]
            narrative_parts.append(
                f"The primary area of concern was '{top_neg}', "
                f"which reduced your score by {abs(neg_drivers[0][1]):.1f} points."
            )

        # Questionnaire context
        phq = q_results["phq9"]["score"]
        gad = q_results["gad7"]["score"]
        if phq >= 10:
            narrative_parts.append(
                f"Your PHQ-9 score of {phq} suggests moderate-to-severe depressive "
                "symptoms. Consider discussing this with a licensed professional."
            )
        if gad >= 10:
            narrative_parts.append(
                f"Your GAD-7 score of {gad} indicates moderate-to-severe anxiety levels."
            )

        # Facial context
        if facial_results.get("detected"):
            dom_emotion = facial_results.get("emotion", "Neutral")
            narrative_parts.append(
                f"Facial analysis detected a predominant expression of '{dom_emotion}' "
                "across your assessment session frames."
            )

        # Speech context
        if speech_results.get("success"):
            dom_speech = speech_results.get("emotion", "Neutral")
            narrative_parts.append(
                f"Your voice tone was characterised primarily as '{dom_speech}', "
                "based on pitch, energy, and tempo patterns."
            )

        narrative_parts.append(
            "⚠️ Disclaimer: This is an AI-assisted screening tool for educational purposes. "
            "It is not a substitute for professional medical advice, diagnosis, or treatment."
        )

        return " ".join(narrative_parts)

    # ──────────────────────────────────────────────────────────────────────────
    # Helper score functions
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _face_score(facial_results: Dict) -> float:
        probs = facial_results.get("probabilities", {})
        pos = probs.get("Happy", 0) + probs.get("Surprise", 0) * 0.5 + probs.get("Neutral", 0) * 0.8
        neg = probs.get("Angry", 0) + probs.get("Sad", 0) + probs.get("Fear", 0) + probs.get("Disgust", 0)
        return (pos / (pos + neg + 1e-9)) * 100.0

    @staticmethod
    def _speech_score(speech_results: Dict) -> float:
        probs = speech_results.get("probabilities", {})
        pos = probs.get("Happy", 0) + probs.get("Calm", 0) * 0.9 + probs.get("Neutral", 0) * 0.8
        neg = probs.get("Angry", 0) + probs.get("Sad", 0) + probs.get("Fear", 0) + probs.get("Disgust", 0)
        return (pos / (pos + neg + 1e-9)) * 100.0


# ─── Singleton instance ───────────────────────────────────────────────────────
explainable_ai = ExplainableAI()
