from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import ChatMessage, ChatSession, SessionFeedback
from datetime import datetime
import uuid
import json
import logging
from typing import AsyncGenerator
from ..rag import rag_instance

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/ask")
async def ask_question(
    request: Request,
    text: dict,
    db: AsyncSession = Depends(get_db)
):
    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            raise HTTPException(status_code=401, detail="No session ID provided")

        # Get session from database
        session = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = session.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")

        # Update session last active timestamp
        if session.session_metadata:
            session.session_metadata["last_active"] = datetime.utcnow().isoformat()
        await db.commit()

        # Get the response from RAG instance
        async def generate():
            try:
                async for token in await rag_instance.stream_query(text["text"], session_id):
                    yield f"data: {json.dumps({'token': token})}\n\n"
            except Exception as e:
                logger.error(f"Error in stream generation: {str(e)}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session")
async def create_session(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        # Check if there's an existing active session for this IP
        client_ip = request.client.host
        existing_session = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == client_ip)
            .order_by(ChatSession.created_at.desc())
        )
        existing_session = existing_session.scalar_one_or_none()

        # If there's an existing session, try to use it
        if existing_session:
            try:
                # Check if the session is still valid in RAG
                if existing_session.id in rag_instance.active_sessions:
                    return {"session_id": existing_session.id, "message": "Using existing session"}
                else:
                    # If RAG session doesn't exist, create a new one
                    await rag_instance._remove_session(existing_session.id)
            except Exception:
                pass  # If there's any error, proceed to create new session

        # Create new session
        session_id = await rag_instance.create_session()
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
            user_id=client_ip,
            session_metadata=metadata
        )
        
        db.add(new_session)
        await db.commit()
        
        return {"session_id": session_id, "message": "New session created successfully"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating session: {str(e)}", exc_info=True)
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
        
        message.thumbs_up = feedback.get("thumbs_up", True)
        message.thumbs_down = feedback.get("thumbs_down", False)
        message.feedback_timestamp = datetime.utcnow()
        
        await db.commit()
        return {"status": "success"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating message feedback: {str(e)}", exc_info=True)
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