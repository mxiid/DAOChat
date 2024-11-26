from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from ..database import get_db
from ..models import ChatMessage, ChatSession
from datetime import datetime
import uuid
import json
import logging
from typing import AsyncGenerator
from ..rag import rag_instance

logger = logging.getLogger(__name__)
router = APIRouter()

def get_client_info(request: Request) -> dict:
    """Extract client information from request"""
    headers = dict(request.headers)
    return {
        "ip_address": request.client.host,
        "user_agent": headers.get("user-agent", "Unknown"),
        "accept_language": headers.get("accept-language", "Unknown"),
        "platform": headers.get("sec-ch-ua-platform", "Unknown").strip('"'),
        "device": {
            "mobile": headers.get("sec-ch-ua-mobile", "Unknown"),
            "platform": headers.get("sec-ch-ua-platform", "Unknown").strip('"'),
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/session")
async def create_session(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        # Get client info
        client_info = get_client_info(request)
        
        # Create new session in RAG first
        session_id = await rag_instance.create_session()
        
        # Update the existing session with client info
        session = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = session.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=500, detail="Failed to create session")
        
        # Update session with client info
        session.user_id = client_info["ip_address"]
        session.session_metadata = client_info
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

        # Update session metadata with latest client info
        session.session_metadata.update(get_client_info(request))
        session.last_activity = datetime.utcnow()
        await db.commit()

        # Get the response from RAG instance
        async def generate():
            bot_response = ""
            bot_message_id = None
            try:
                async for token in await rag_instance.stream_query(text["text"], session_id):
                    bot_response += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
                
                # Create bot message after complete response
                bot_message = ChatMessage(
                    session_id=session_id,
                    role='bot',
                    content=bot_response,
                    message_metadata={
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                db.add(bot_message)
                await db.commit()
                await db.refresh(bot_message)
                bot_message_id = bot_message.id
                
                # Send message ID in a special message
                yield f"data: {json.dumps({'message_id': bot_message_id})}\n\n"
                
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
        
        message.thumbs_up = feedback.get("thumbs_up", False)
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