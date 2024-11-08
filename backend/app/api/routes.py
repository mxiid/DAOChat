from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import logging
from ..rag import ask_question, suggest_questions, rag_instance
from slowapi import Limiter
from slowapi.util import get_remote_address
import time
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize limiter with storage
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
router = APIRouter()

class Question(BaseModel):
    text: str

class Answer(BaseModel):
    text: str

@router.post("/ask")
async def ask(
    question: Question, 
    request: Request, 
    background_tasks: BackgroundTasks
):
    try:
        # Log the incoming request
        logger.info(f"Received question: {question.text}")
        
        session_id = request.headers.get("X-Session-ID", "default")
        
        async def generate():
            async for token in rag_instance.stream_query(question.text, session_id):
                yield f"data: {json.dumps({'token': token})}\n\n"
        
        # Cleanup in background
        background_tasks.add_task(cleanup_session, session_id)
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suggest_questions", response_model=List[str])
async def suggest(context: str, request: Request):
    try:
        questions = await suggest_questions(context)
        return questions
    except Exception as e:
        logger.error(f"Error suggesting questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask/stream")
async def ask_stream(
    question: Question,
    request: Request,
    background_tasks: BackgroundTasks
):
    try:
        session_id = request.headers.get("X-Session-ID", "default")
        
        async def generate():
            async for token in rag_instance.stream_query(question.text, session_id):
                yield f"data: {json.dumps({'token': token})}\n\n"
        
        # Cleanup in background
        background_tasks.add_task(cleanup_session, session_id)
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"Error processing streaming request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def cleanup_session(session_id: str):
    """Cleanup session data after request completion"""
    try:
        # Only clean up if the session has been inactive for more than the TTL
        current_time = time.time()
        if (session_id in rag_instance.last_access and 
            current_time - rag_instance.last_access[session_id] > rag_instance.memory_ttl):
            
            if session_id in rag_instance.memory_pools:
                del rag_instance.memory_pools[session_id]
            if session_id in rag_instance.last_access:
                del rag_instance.last_access[session_id]
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {e}")