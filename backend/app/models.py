import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    bio = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    timezone = Column(String, default="UTC")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)
    # Streak tracking
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_assessment_date = Column(DateTime, nullable=True)

    sessions = relationship("AssessmentSession", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed = Column(Boolean, default=False)
    # Dominant emotions from modalities
    facial_emotion = Column(String, nullable=True)
    speech_emotion = Column(String, nullable=True)
    # Raw clinical subscale scores
    phq9_score = Column(Integer, nullable=True)
    gad7_score = Column(Integer, nullable=True)
    pss_score = Column(Integer, nullable=True)
    who5_score = Column(Float, nullable=True)

    user = relationship("User", back_populates="sessions")
    results = relationship("AssessmentResult", back_populates="session", cascade="all, delete-orphan")


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("assessment_sessions.id"), nullable=False)
    facial_score = Column(Float)          # normalised (0–100)
    speech_score = Column(Float)          # normalised (0–100)
    questionnaire_score = Column(Float)   # normalised (0–100)
    fused_score = Column(Float)           # final fused score (0–100)
    confidence = Column(Float)            # model confidence (0–1)
    classification = Column(String)       # Healthy | Mild Stress | ... | Depression Risk
    explainability_data = Column(Text)    # JSON – SHAP/LIME attributions
    recommendations = Column(Text)        # JSON – personalised recommendations
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("AssessmentSession", back_populates="results")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender = Column(String, nullable=False)   # "user" or "bot"
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="chats")
