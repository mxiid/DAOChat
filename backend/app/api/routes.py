from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import List
import logging
from ..rag import ask_question, suggest_questions
from slowapi import Limiter
from slowapi.util import get_remote_address

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

class Question(BaseModel):
    text: str

class Answer(BaseModel):
    text: str

@router.post("/ask", response_model=Answer)
@limiter.limit("30/minute")  # Rate limit per IP
async def ask(
    question: Question, 
    request: Request, 
    background_tasks: BackgroundTasks
):
    try:
        session_id = request.headers.get("X-Session-ID", "default")
        answer = await ask_question(question.text, session_id)
        
        # Cleanup in background
        background_tasks.add_task(cleanup_session, session_id)
        
        return Answer(text=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suggest_questions", response_model=List[str])
async def suggest(context: str):
    try:
        questions = await suggest_questions(context)
        return questions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))