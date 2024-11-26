from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
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

@router.post("/session")
async def create_session(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        # Get client IP and user agent
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "Unknown")

        # Create new session in RAG first
        session_id = await rag_instance.create_session()
        
        # Check if session already exists
        existing_session = await db.execute(
            text("""
                SELECT id FROM chatbot.chat_sessions 
                WHERE id = :session_id
            """),
            {"session_id": session_id}
        )
        if existing_session.scalar_one_or_none():
            # If session exists, clean up RAG session and try again
            await rag_instance._remove_session(session_id)
            # Recursive call to try again with a new session ID
            return await create_session(request, db)
        
        # Create metadata
        metadata = {
            "ip_address": client_ip,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
            "last_active": datetime.utcnow().isoformat()
        }

        # Deactivate old sessions
        await db.execute(
            text("""
                UPDATE chatbot.chat_sessions 
                SET is_active = false, 
                    ended_at = NOW() 
                WHERE user_id = :user_id 
                AND is_active = true
                AND id != :session_id
            """),
            {
                "user_id": client_ip,
                "session_id": session_id
            }
        )
        
        # Create new session
        await db.execute(
            text("""
                INSERT INTO chatbot.chat_sessions 
                (id, user_id, created_at, session_metadata, is_active, ended_at)
                VALUES 
                (:id, :user_id, NOW(), :metadata, true, NULL)
            """),
            {
                "id": session_id,
                "user_id": client_ip,
                "metadata": json.dumps(metadata)
            }
        )
        
        await db.commit()
        
        return {
            "session_id": session_id,
            "message": "New session created successfully"
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating session: {str(e)}", exc_info=True)
        
        # If we failed after creating RAG session, clean it up
        if 'session_id' in locals():
            try:
                await rag_instance._remove_session(session_id)
            except Exception:
                pass
        
        raise HTTPException(status_code=500, detail=str(e))

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
            select(ChatSession)
            .where(
                ChatSession.id == session_id,
                ChatSession.is_active == True
            )
        )
        session = session.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=401, detail="Invalid or inactive session")

        # Verify session exists in RAG
        if session_id not in rag_instance.active_sessions:
            # Mark session as inactive
            session.is_active = False
            session.ended_at = datetime.utcnow()
            await db.commit()
            raise HTTPException(status_code=401, detail="Session expired. Please create a new session.")

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
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """End a chat session"""
    try:
        session = await db.execute(
            select(ChatSession)
            .where(
                ChatSession.id == session_id,
                ChatSession.is_active == True
            )
        )
        session = session.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Active session not found")
        
        # Mark session as inactive
        session.is_active = False
        session.ended_at = datetime.utcnow()
        
        # Remove from RAG if it exists
        if session_id in rag_instance.active_sessions:
            await rag_instance._remove_session(session_id)
        
        await db.commit()
        return JSONResponse({
            "message": "Session ended successfully"
        })
    except HTTPException as he:
        raise he
    except Exception as e:
        await db.rollback()
        logger.error(f"Error ending session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))