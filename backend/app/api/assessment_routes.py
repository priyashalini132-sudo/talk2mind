import base64
import os
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from ..database import get_db
from .. import crud, schemas, auth
from ..config import settings
from ..ml.facial_model import facial_recognizer
from ..ml.speech_model import speech_recognizer
from ..ml.questionnaire import questionnaire_scorer
from ..ml.fusion_model import fusion_model
from ..ml.explainability import explainable_ai
from ..ml.recommendation import recommendation_engine

router = APIRouter(prefix="/assessment", tags=["Assessment & Diagnostics"])

# In-memory storage for intermediate session details (frame probabilities & audio outputs)
# Keys: session_id, Value: {"frames": [dict], "audio": dict}
session_cache: Dict[int, Dict[str, Any]] = {}

@router.post("/session/start", response_model=schemas.AssessmentSessionOut)
def start_assessment(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
):
    session = crud.create_session(db, user_id=current_user.id)
    session_cache[session.id] = {"frames": [], "audio": None}
    return session

@router.post("/session/{session_id}/analyze-frame")
def analyze_frame(
    session_id: int,
    frame_data: Dict[str, str], # {"frame": "data:image/jpeg;base64,... "}
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
):
    session = crud.get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Assessment session not found")
        
    if session.completed:
        raise HTTPException(status_code=400, detail="Session is already completed")
        
    base64_str = frame_data.get("frame")
    if not base64_str:
        raise HTTPException(status_code=400, detail="Missing base64 frame string")
        
    try:
        # Strip header if present
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
            
        frame_bytes = base64.b64decode(base64_str)
        result = facial_recognizer.predict(frame_bytes)
        
        # Cache frame metrics if face was successfully detected
        if result["detected"]:
            if session_id not in session_cache:
                session_cache[session_id] = {"frames": [], "audio": None}
            session_cache[session_id]["frames"].append(result)
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Frame processing failed: {str(e)}")

@router.post("/session/{session_id}/upload-audio")
async def upload_audio(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
):
    session = crud.get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Assessment session not found")
        
    if session.completed:
        raise HTTPException(status_code=400, detail="Session is already completed")
        
    file_path = os.path.join(settings.UPLOAD_DIR, f"session_{session_id}.wav")
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        # Run speech analysis
        result = speech_recognizer.predict(file_path)
        
        # Cache speech metrics
        if session_id not in session_cache:
            session_cache[session_id] = {"frames": [], "audio": None}
        session_cache[session_id]["audio"] = result
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")

@router.post("/session/{session_id}/submit", response_model=schemas.AssessmentResultOut)
def submit_assessment(
    session_id: int,
    questionnaire: schemas.QuestionnaireSubmission,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
):
    session = crud.get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Assessment session not found")
        
    if session.completed:
        raise HTTPException(status_code=400, detail="Session is already completed")
        
    # Get Cached Visual & Audio results
    cache = session_cache.get(session_id, {"frames": [], "audio": None})
    
    # 1. Aggregate Visual Results
    facial_result = {"detected": False, "probabilities": {}, "confidence": 0.0}
    if cache["frames"]:
        # Average emotion probabilities across all captured frames in the session
        facial_result["detected"] = True
        probabilities_sum = {}
        for frame in cache["frames"]:
            for emotion, prob in frame["probabilities"].items():
                probabilities_sum[emotion] = probabilities_sum.get(emotion, 0.0) + prob
                
        num_frames = len(cache["frames"])
        facial_result["probabilities"] = {e: v / num_frames for e, v in probabilities_sum.items()}
        facial_result["confidence"] = sum(f["confidence"] for f in cache["frames"]) / num_frames
        
    # 2. Get Speech Results
    speech_result = cache["audio"] if cache["audio"] else {"success": False, "probabilities": {}, "confidence": 0.0}
    
    # 3. Calculate Questionnaire Score
    try:
        q_results = questionnaire_scorer.calculate_overall(
            phq9=questionnaire.phq9,
            gad7=questionnaire.gad7,
            pss=questionnaire.pss,
            who5=questionnaire.who5
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # 4. Multimodal Fusion
    fused_results = fusion_model.fuse(
        questionnaire_results=q_results,
        facial_results=facial_result,
        speech_results=speech_result
    )
    
    # 5. Explainable AI (SHAP descriptions)
    explain_data = explainable_ai.generate_explanation(
        fused_score=fused_results["fused_score"],
        q_results=q_results,
        facial_results=facial_result,
        speech_results=speech_result
    )
    
    # 6. Recommendations
    recs = recommendation_engine.generate_recommendations(
        score=fused_results["fused_score"],
        classification=fused_results["classification"],
        q_results=q_results
    )
    
    # Build database payload
    db_result_payload = schemas.AssessmentResultCreate(
        facial_score=fused_results["facial_score"] if fused_results["facial_score"] is not None else 0.0,
        speech_score=fused_results["speech_score"] if fused_results["speech_score"] is not None else 0.0,
        questionnaire_score=fused_results["questionnaire_score"],
        fused_score=fused_results["fused_score"],
        confidence=fused_results["confidence"],
        classification=fused_results["classification"],
        explainability_data=json.dumps(explain_data),
        recommendations=json.dumps(recs)
    )
    
    # Commit to DB
    db_result = crud.create_result(db, session_id=session_id, result=db_result_payload)

    # Update session with emotion metadata and subscale scores
    crud.complete_session(
        db,
        session_id=session_id,
        facial_emotion=facial_result.get("emotion") if facial_result.get("detected") else None,
        speech_emotion=speech_result.get("emotion") if speech_result.get("success") else None,
        phq9=sum(questionnaire.phq9) if questionnaire.phq9 else None,
        gad7=sum(questionnaire.gad7) if questionnaire.gad7 else None,
        pss=sum(questionnaire.pss) if questionnaire.pss else None,
        who5=sum(questionnaire.who5) if questionnaire.who5 else None,
    )

    # Update user streak
    crud.update_user_streak(db, user_id=current_user.id)

    # Clean cache
    if session_id in session_cache:
        del session_cache[session_id]

    # Clean uploaded audio file to save space
    audio_path = os.path.join(settings.UPLOAD_DIR, f"session_{session_id}.wav")
    if os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except Exception:
            pass

    return db_result
