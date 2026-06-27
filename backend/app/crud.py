import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas, auth


# ─── User CRUD ────────────────────────────────────────────────────────────────

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_pw = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_pw
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, db_user: models.User, user_update: schemas.UserUpdate):
    if user_update.email is not None:
        db_user.email = user_update.email
    if user_update.full_name is not None:
        db_user.full_name = user_update.full_name
    if user_update.password is not None:
        db_user.hashed_password = auth.get_password_hash(user_update.password)
    if user_update.bio is not None:
        db_user.bio = user_update.bio
    if user_update.age is not None:
        db_user.age = user_update.age
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_streak(db: Session, user_id: int):
    """Update streak counter after a completed assessment."""
    db_user = get_user(db, user_id)
    if not db_user:
        return
    today = datetime.date.today()
    last_date = db_user.last_assessment_date.date() if db_user.last_assessment_date else None

    if last_date is None:
        db_user.current_streak = 1
    elif last_date == today:
        pass  # Already assessed today
    elif last_date == today - datetime.timedelta(days=1):
        db_user.current_streak += 1
    else:
        db_user.current_streak = 1  # Streak broken

    db_user.longest_streak = max(db_user.current_streak, db_user.longest_streak or 0)
    db_user.last_assessment_date = datetime.datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user


# ─── Session CRUD ─────────────────────────────────────────────────────────────

def create_session(db: Session, user_id: int):
    db_session = models.AssessmentSession(user_id=user_id, completed=False)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_session(db: Session, session_id: int):
    return db.query(models.AssessmentSession).filter(
        models.AssessmentSession.id == session_id
    ).first()

def get_user_sessions(db: Session, user_id: int, limit: int = 50):
    return db.query(models.AssessmentSession).filter(
        models.AssessmentSession.user_id == user_id
    ).order_by(models.AssessmentSession.created_at.desc()).limit(limit).all()

def complete_session(
    db: Session,
    session_id: int,
    facial_emotion: str = None,
    speech_emotion: str = None,
    phq9: int = None,
    gad7: int = None,
    pss: int = None,
    who5: float = None,
):
    db_session = get_session(db, session_id)
    if db_session:
        db_session.completed = True
        if facial_emotion: db_session.facial_emotion = facial_emotion
        if speech_emotion: db_session.speech_emotion = speech_emotion
        if phq9 is not None: db_session.phq9_score = phq9
        if gad7 is not None: db_session.gad7_score = gad7
        if pss is not None:  db_session.pss_score = pss
        if who5 is not None: db_session.who5_score = who5
        db.commit()
        db.refresh(db_session)
    return db_session


# ─── Results CRUD ─────────────────────────────────────────────────────────────

def create_result(db: Session, session_id: int, result: schemas.AssessmentResultCreate):
    db_result = models.AssessmentResult(
        session_id=session_id,
        facial_score=result.facial_score,
        speech_score=result.speech_score,
        questionnaire_score=result.questionnaire_score,
        fused_score=result.fused_score,
        confidence=result.confidence,
        classification=result.classification,
        explainability_data=result.explainability_data,
        recommendations=result.recommendations
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

def get_user_results(db: Session, user_id: int, limit: int = 100):
    return db.query(models.AssessmentResult).join(
        models.AssessmentSession
    ).filter(
        models.AssessmentSession.user_id == user_id
    ).order_by(
        models.AssessmentResult.created_at.desc()
    ).limit(limit).all()

def get_result_by_id(db: Session, result_id: int):
    return db.query(models.AssessmentResult).filter(
        models.AssessmentResult.id == result_id
    ).first()

def get_weekly_average(db: Session, user_id: int) -> float:
    """Average fused score over the last 7 days."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    results = db.query(models.AssessmentResult).join(
        models.AssessmentSession
    ).filter(
        models.AssessmentSession.user_id == user_id,
        models.AssessmentResult.created_at >= cutoff
    ).all()
    if not results:
        return 0.0
    return round(sum(r.fused_score for r in results) / len(results), 1)

def get_monthly_average(db: Session, user_id: int) -> float:
    """Average fused score over the last 30 days."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    results = db.query(models.AssessmentResult).join(
        models.AssessmentSession
    ).filter(
        models.AssessmentSession.user_id == user_id,
        models.AssessmentResult.created_at >= cutoff
    ).all()
    if not results:
        return 0.0
    return round(sum(r.fused_score for r in results) / len(results), 1)

def get_emotion_timeline(db: Session, user_id: int, limit: int = 20):
    """Return sessions with emotion data for timeline visualisation."""
    return db.query(models.AssessmentSession).filter(
        models.AssessmentSession.user_id == user_id,
        models.AssessmentSession.completed == True,
    ).order_by(models.AssessmentSession.created_at.desc()).limit(limit).all()

def get_score_history(db: Session, user_id: int, limit: int = 30):
    """Return fused scores with dates for trend chart."""
    results = db.query(models.AssessmentResult).join(
        models.AssessmentSession
    ).filter(
        models.AssessmentSession.user_id == user_id
    ).order_by(
        models.AssessmentResult.created_at.asc()
    ).limit(limit).all()
    return [
        {
            "date": r.created_at.strftime("%b %d"),
            "score": r.fused_score,
            "classification": r.classification,
        }
        for r in results
    ]

def get_classification_distribution(db: Session, user_id: int):
    """Return count of each classification for pie/bar chart."""
    results = db.query(
        models.AssessmentResult.classification,
        func.count(models.AssessmentResult.id).label("count")
    ).join(models.AssessmentSession).filter(
        models.AssessmentSession.user_id == user_id
    ).group_by(models.AssessmentResult.classification).all()
    return {r.classification: r.count for r in results}


# ─── Chat CRUD ────────────────────────────────────────────────────────────────

def create_chat_message(db: Session, user_id: int, sender: str, message: str):
    db_msg = models.ChatHistory(user_id=user_id, sender=sender, message=message)
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg

def get_user_chats(db: Session, user_id: int, limit: int = 50):
    return db.query(models.ChatHistory).filter(
        models.ChatHistory.user_id == user_id
    ).order_by(models.ChatHistory.created_at.asc()).limit(limit).all()

def clear_user_chats(db: Session, user_id: int):
    db.query(models.ChatHistory).filter(
        models.ChatHistory.user_id == user_id
    ).delete()
    db.commit()
