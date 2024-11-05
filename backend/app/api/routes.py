from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List
import logging
from ..rag import ask_question, suggest_questions, rag_instance
from slowapi import Limiter
from slowapi.util import get_remote_address

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

@router.post("/ask", response_model=Answer)
async def ask(
    question: Question, 
    request: Request, 
    background_tasks: BackgroundTasks
):
    try:
        # Log the incoming request
        logger.info(f"Received question: {question.text}")
        
        session_id = request.headers.get("X-Session-ID", "default")
        answer = await ask_question(question.text, session_id)
        
        # Cleanup in background
        background_tasks.add_task(cleanup_session, session_id)
        
        return Answer(text=answer)
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

async def cleanup_session(session_id: str):
    """Cleanup session data after request completion"""
    try:
        if session_id in rag_instance.memory_pools:
            del rag_instance.memory_pools[session_id]
        if hasattr(rag_instance.response_cache, 'cache'):
            cache = rag_instance.response_cache.cache
            keys_to_delete = [k for k in cache.keys() if k.startswith(f"{session_id}:")]
            for k in keys_to_delete:
                del cache[k]
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {e}")