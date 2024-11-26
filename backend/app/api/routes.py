from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
from ..rag import rag_instance
from slowapi import Limiter
from slowapi.util import get_remote_address
import json
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import ChatMessage, ChatSession, SessionFeedback
from datetime import datetime
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize limiter
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
router = APIRouter()

class Question(BaseModel):
    text: str

@router.post("/session")
async def create_session(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        session_id = str(uuid.uuid4())
        
        # Get client IP and user agent
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "Unknown")
        
        # Create metadata
        metadata = {
            "ip_address": client_ip,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
            "last_active": datetime.utcnow().isoformat()
        }
        
        new_session = ChatSession(
            id=session_id,
            user_id=client_ip,  # Store IP as user_id
            session_metadata=metadata
        )
        
        db.add(new_session)
        await db.commit()
        
        return {"session_id": session_id}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask")
async def ask_stream(
    question: Question,
    request: Request,
    background_tasks: BackgroundTasks
):
    """Stream responses to questions using RAG"""
    try:
        session_id = request.headers.get("X-Session-ID")
        
        # Validate session
        if not session_id:
            raise HTTPException(
                status_code=400,
                detail="X-Session-ID header is required. Please create a new session."
            )
            
        if session_id not in rag_instance.active_sessions:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session. Please create a new session."
            )

        logger.info(f"Processing question for session {session_id}: {question.text}")
        
        async def generate():
            try:
                # Get the async generator from stream_query
                generator = await rag_instance.stream_query(question.text, session_id)
                async for token in generator:
                    yield f"data: {json.dumps({'token': token})}\n\n"
            except Exception as e:
                logger.error(f"Error in stream generation: {str(e)}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        response = StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
        response.headers["X-Session-ID"] = session_id
        return response
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing streaming request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suggest_questions", response_model=List[str])
async def suggest(
    context: str,
    request: Request
):
    """Generate suggested follow-up questions"""
    try:
        session_id = request.headers.get("X-Session-ID")
        
        # Validate session
        if not session_id:
            raise HTTPException(
                status_code=400,
                detail="X-Session-ID header is required"
            )
            
        if session_id not in rag_instance.active_sessions:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session"
            )

        questions = await rag_instance.generate_questions(context)
        return questions
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error suggesting questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}")
async def end_session(session_id: str):
    """End a chat session"""
    try:
        if session_id not in rag_instance.active_sessions:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        await rag_instance._remove_session(session_id)
        return JSONResponse({
            "message": "Session ended successfully"
        })
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error ending session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message/{message_id}/feedback")
async def message_feedback(
    message_id: int,
    feedback: dict,
    db: AsyncSession = Depends(get_db)
):
    try:
        message = await db.get(ChatMessage, message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        message.thumbs_up = feedback.get("thumbs_up", True)  # Default to True for thumbs up
        message.thumbs_down = feedback.get("thumbs_down", False)
        message.feedback_timestamp = datetime.utcnow()
        
        await db.commit()
        return {"status": "success"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating message feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/{session_id}/feedback")
async def session_feedback(
    session_id: str,
    rating: int,
    feedback_text: str = None,
    email: str = None,
    db: AsyncSession = Depends(get_db)
):
    if not 1 <= rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    feedback = SessionFeedback(
        session_id=session_id,
        rating=rating,
        feedback_text=feedback_text,
        email=email
    )
    
    db.add(feedback)
    await db.commit()
    return {"status": "success"}

@router.post("/session/metadata")
async def update_session_metadata(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get client IP
    client_ip = request.client.host
    
    # Get user agent info
    user_agent = request.headers.get("user-agent", "")
    
    # Update session metadata
    metadata = {
        "ip_address": client_ip,
        "user_agent": user_agent,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    session.user_id = client_ip  # Store IP as user_id
    session.session_metadata = metadata
    
    await db.commit()
    return {"status": "success"}