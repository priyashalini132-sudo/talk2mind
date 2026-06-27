"""
Talk2Mind – Reports API Routes
================================
Provides weekly and monthly mental wellness report generation.
"""

import json
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from ..database import get_db
from .. import crud, auth, schemas

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/weekly")
def get_weekly_report(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
) -> Dict[str, Any]:
    """
    Generate a comprehensive weekly mental wellness report for the authenticated user.
    Covers the past 7 days of assessments.
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    results = crud.get_user_results(db, current_user.id)
    weekly = [r for r in results if r.created_at >= cutoff]

    if not weekly:
        return {
            "period": "Last 7 Days",
            "total_assessments": 0,
            "message": "No assessments recorded this week. Take your first one today!",
            "average_score": None,
            "best_score": None,
            "worst_score": None,
            "dominant_classification": None,
            "trend": "N/A",
            "daily_breakdown": [],
        }

    scores = [r.fused_score for r in weekly]
    classifications = [r.classification for r in weekly]
    dominant = max(set(classifications), key=classifications.count)

    # Trend: compare first half vs second half
    mid = len(scores) // 2
    if mid > 0:
        first_half = sum(scores[:mid]) / mid
        second_half = sum(scores[mid:]) / (len(scores) - mid)
        trend = "Improving ↑" if second_half > first_half + 2 else (
                "Declining ↓" if second_half < first_half - 2 else "Stable →")
    else:
        trend = "Stable →"

    # Daily breakdown
    daily = {}
    for r in weekly:
        day_key = r.created_at.strftime("%A, %b %d")
        if day_key not in daily:
            daily[day_key] = []
        daily[day_key].append(r.fused_score)

    daily_breakdown = [
        {"day": day, "avg_score": round(sum(v) / len(v), 1), "sessions": len(v)}
        for day, v in daily.items()
    ]

    # Classification distribution this week
    dist: Dict[str, int] = {}
    for c in classifications:
        dist[c] = dist.get(c, 0) + 1

    return {
        "period": "Last 7 Days",
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "total_assessments": len(weekly),
        "average_score": round(sum(scores) / len(scores), 1),
        "best_score": round(max(scores), 1),
        "worst_score": round(min(scores), 1),
        "dominant_classification": dominant,
        "trend": trend,
        "classification_distribution": dist,
        "daily_breakdown": daily_breakdown,
        "recommendation_summary": _summarise_recommendations(weekly),
    }


@router.get("/monthly")
def get_monthly_report(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
) -> Dict[str, Any]:
    """
    Generate a monthly mental wellness report for the authenticated user.
    Covers the past 30 days.
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    results = crud.get_user_results(db, current_user.id)
    monthly = [r for r in results if r.created_at >= cutoff]

    if not monthly:
        return {
            "period": "Last 30 Days",
            "total_assessments": 0,
            "message": "No assessments in the past month.",
        }

    scores = [r.fused_score for r in monthly]
    classifications = [r.classification for r in monthly]
    dist: Dict[str, int] = {}
    for c in classifications:
        dist[c] = dist.get(c, 0) + 1

    # Weekly sub-averages
    weekly_avgs = []
    for week_num in range(4):
        start = cutoff + datetime.timedelta(days=week_num * 7)
        end = start + datetime.timedelta(days=7)
        week_scores = [r.fused_score for r in monthly if start <= r.created_at < end]
        if week_scores:
            weekly_avgs.append({
                "week": f"Week {week_num + 1}",
                "avg_score": round(sum(week_scores) / len(week_scores), 1),
                "sessions": len(week_scores),
            })

    # Overall trend
    if len(scores) >= 4:
        q1 = sum(scores[:len(scores)//4]) / (len(scores)//4)
        q4 = sum(scores[3*len(scores)//4:]) / (len(scores) - 3*len(scores)//4)
        trend = "Improving ↑" if q4 > q1 + 3 else ("Declining ↓" if q4 < q1 - 3 else "Stable →")
    else:
        trend = "Stable →"

    return {
        "period": "Last 30 Days",
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "total_assessments": len(monthly),
        "average_score": round(sum(scores) / len(scores), 1),
        "best_score": round(max(scores), 1),
        "worst_score": round(min(scores), 1),
        "score_std_dev": round(_std_dev(scores), 1),
        "dominant_classification": max(set(classifications), key=classifications.count),
        "trend": trend,
        "classification_distribution": dist,
        "weekly_breakdown": weekly_avgs,
        "consistency_score": round(len(monthly) / 30.0 * 100, 1),  # % of days with assessment
    }


@router.get("/all-time")
def get_alltime_stats(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
) -> Dict[str, Any]:
    """Return aggregate lifetime statistics for the user."""
    results = crud.get_user_results(db, current_user.id)
    if not results:
        return {"total_assessments": 0, "message": "No data yet."}

    scores = [r.fused_score for r in results]
    classifications = [r.classification for r in results]
    dist: Dict[str, int] = {}
    for c in classifications:
        dist[c] = dist.get(c, 0) + 1

    user = crud.get_user(db, current_user.id)
    return {
        "total_assessments": len(results),
        "lifetime_average": round(sum(scores) / len(scores), 1),
        "all_time_best": round(max(scores), 1),
        "all_time_worst": round(min(scores), 1),
        "current_streak": user.current_streak if user else 0,
        "longest_streak": user.longest_streak if user else 0,
        "first_assessment": results[-1].created_at.strftime("%B %d, %Y"),
        "classification_distribution": dist,
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _std_dev(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance ** 0.5

def _summarise_recommendations(results):
    """Extract most common recommendation categories from recent results."""
    categories = {}
    for r in results:
        try:
            recs = json.loads(r.recommendations)
            for cat, items in recs.items():
                if isinstance(items, list) and items:
                    categories[cat] = categories.get(cat, 0) + 1
        except Exception:
            pass
    if not categories:
        return []
    top = sorted(categories.items(), key=lambda x: -x[1])[:3]
    return [{"category": cat, "frequency": freq} for cat, freq in top]
