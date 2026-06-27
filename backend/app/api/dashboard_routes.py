"""
Talk2Mind – Enhanced Dashboard API Routes
==========================================
Provides comprehensive analytics endpoints:
  - Summary dashboard (scores, streak, latest result)
  - Emotion timeline (per-session emotions)
  - Modality breakdown (questionnaire vs face vs speech)
  - Score history (for trend charts)
  - Classification distribution (for pie chart)
"""

import json
import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from ..database import get_db
from .. import crud, auth, schemas

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
) -> Dict[str, Any]:
    """
    Returns the full dashboard summary payload:
      - Last assessment result
      - Score history (trend chart)
      - Weekly / monthly averages
      - Emotion timeline
      - Classification distribution
      - User streak
    """
    all_results = crud.get_user_results(db, current_user.id)
    user = crud.get_user(db, current_user.id)

    if not all_results:
        return {
            "total_assessments": 0,
            "last_assessment": None,
            "score_history": [],
            "emotion_timeline": [],
            "weekly_average": 0.0,
            "monthly_average": 0.0,
            "classification_distribution": {},
            "current_streak": 0,
            "longest_streak": 0,
            "modality_breakdown": [],
        }

    latest = all_results[0]

    # Parse explainability for modality breakdown
    modality_breakdown = []
    try:
        xai_data = json.loads(latest.explainability_data)
        modality_weights = xai_data.get("modality_weights", {})
        modality_breakdown = [
            {"modality": k, "weight_pct": v}
            for k, v in modality_weights.items()
        ]
    except Exception:
        modality_breakdown = [
            {"modality": "Questionnaire", "weight_pct": 100.0}
        ]

    # Score history (ascending date order for chart)
    score_history = crud.get_score_history(db, current_user.id, limit=30)

    # Emotion timeline
    timeline_sessions = crud.get_emotion_timeline(db, current_user.id, limit=20)
    emotion_timeline = []
    for sess in timeline_sessions:
        result = sess.results[0] if sess.results else None
        emotion_timeline.append({
            "date": sess.created_at.strftime("%b %d, %H:%M"),
            "facial_emotion": sess.facial_emotion or "N/A",
            "speech_emotion": sess.speech_emotion or "N/A",
            "fused_score": result.fused_score if result else None,
            "classification": result.classification if result else None,
        })

    # Classification distribution (for donut/pie chart)
    dist = crud.get_classification_distribution(db, current_user.id)

    return {
        "total_assessments": len(all_results),
        "last_assessment": {
            "id": latest.id,
            "fused_score": latest.fused_score,
            "facial_score": latest.facial_score,
            "speech_score": latest.speech_score,
            "questionnaire_score": latest.questionnaire_score,
            "confidence": latest.confidence,
            "classification": latest.classification,
            "created_at": latest.created_at.isoformat(),
            "explainability_data": latest.explainability_data,
            "recommendations": latest.recommendations,
        },
        "score_history": score_history,
        "emotion_timeline": emotion_timeline,
        "weekly_average": crud.get_weekly_average(db, current_user.id),
        "monthly_average": crud.get_monthly_average(db, current_user.id),
        "classification_distribution": dist,
        "modality_breakdown": modality_breakdown,
        "current_streak": user.current_streak if user else 0,
        "longest_streak": user.longest_streak if user else 0,
    }


@router.get("/history")
def get_assessment_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
) -> List[Dict[str, Any]]:
    """Returns paginated assessment history for the profile page."""
    results = crud.get_user_results(db, current_user.id, limit=limit)
    return [
        {
            "id": r.id,
            "fused_score": r.fused_score,
            "classification": r.classification,
            "confidence": r.confidence,
            "facial_score": r.facial_score,
            "speech_score": r.speech_score,
            "questionnaire_score": r.questionnaire_score,
            "created_at": r.created_at.isoformat(),
        }
        for r in results
    ]


@router.get("/result/{result_id}")
def get_result_detail(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
) -> Dict[str, Any]:
    """Returns full detail for a single assessment result."""
    result = crud.get_result_by_id(db, result_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Result not found")
    return {
        "id": result.id,
        "fused_score": result.fused_score,
        "facial_score": result.facial_score,
        "speech_score": result.speech_score,
        "questionnaire_score": result.questionnaire_score,
        "confidence": result.confidence,
        "classification": result.classification,
        "created_at": result.created_at.isoformat(),
        "explainability_data": json.loads(result.explainability_data) if result.explainability_data else {},
        "recommendations": json.loads(result.recommendations) if result.recommendations else {},
    }
