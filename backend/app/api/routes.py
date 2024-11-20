from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
from ..rag import rag_instance
from slowapi import Limiter
from slowapi.util import get_remote_address
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize limiter
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
router = APIRouter()

class Question(BaseModel):
    text: str

@router.post("/session")
async def create_session(request: Request):
    """Create a new chat session"""
    try:
        session_id = await rag_instance.create_session()
        return JSONResponse({
            "session_id": session_id,
            "message": "New session created successfully"
        })
    except Exception as e:
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