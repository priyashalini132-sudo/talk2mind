from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Dict, Any, Optional

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

class UserOut(UserBase):
    id: int
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

# Questionnaire Schemas
class QuestionnaireSubmission(BaseModel):
    # Questions from scales: phq9 (9 questions, 0-3), gad7 (7 questions, 0-3), pss10 (10 questions, 0-4), who5 (5 questions, 0-5)
    phq9: List[int]
    gad7: List[int]
    pss: List[int]
    who5: List[int]

# Session & Results Schemas
class AssessmentResultCreate(BaseModel):
    facial_score: float
    speech_score: float
    questionnaire_score: float
    fused_score: float
    confidence: float
    classification: str
    explainability_data: str  # JSON String
    recommendations: str  # JSON String

class AssessmentResultOut(BaseModel):
    id: int
    session_id: int
    facial_score: float
    speech_score: float
    questionnaire_score: float
    fused_score: float
    confidence: float
    classification: str
    explainability_data: str  # JSON String
    recommendations: str  # JSON String
    created_at: datetime

    class Config:
        from_attributes = True

class AssessmentSessionCreate(BaseModel):
    pass

class AssessmentSessionOut(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    completed: bool
    results: List[AssessmentResultOut] = []

    class Config:
        from_attributes = True

# Chatbot Schemas
class ChatMessageCreate(BaseModel):
    message: str

class ChatMessageOut(BaseModel):
    id: int
    user_id: int
    sender: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True

# Overall API Responses
class DashboardSummary(BaseModel):
    total_assessments: int
    last_assessment: Optional[AssessmentResultOut] = None
    score_history: List[Dict[str, Any]]
    emotion_timeline: List[Dict[str, Any]]
    weekly_average: float
    monthly_average: float
