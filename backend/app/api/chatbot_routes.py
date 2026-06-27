from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import crud, schemas, auth
from ..ml.chatbot import chatbot

router = APIRouter(prefix="/chatbot", tags=["AI Wellness Companion"])

@router.get("/history", response_model=List[schemas.ChatMessageOut])
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
):
    return crud.get_user_chats(db, user_id=current_user.id)

@router.post("/message", response_model=schemas.ChatMessageOut)
def send_chat_message(
    payload: schemas.ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_user)
):
    # Fetch recent history for LLM context (if key is set)
    db_history = crud.get_user_chats(db, user_id=current_user.id, limit=10)
    history = [{"sender": msg.sender, "message": msg.message} for msg in db_history]
    
    # Save User message to DB
    crud.create_chat_message(db, user_id=current_user.id, sender="user", message=payload.message)
    
    # Generate bot response
    bot_response = chatbot.generate_response(user_message=payload.message, chat_history=history)
    
    # Save Bot message to DB
    db_bot_msg = crud.create_chat_message(db, user_id=current_user.id, sender="bot", message=bot_response)
    
    return db_bot_msg
