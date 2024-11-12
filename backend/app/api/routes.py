from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
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

@router.post("/ask")
async def ask_stream(
    question: Question,
    request: Request,
    background_tasks: BackgroundTasks
):
    """Stream responses to questions using RAG"""
    try:
        logger.info(f"Received question: {question.text}")
        session_id = request.headers.get("X-Session-ID", "default")
        
        async def generate():
            async for token in rag_instance.stream_query(question.text, session_id):
                yield f"data: {json.dumps({'token': token})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"Error processing streaming request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suggest_questions", response_model=List[str])
async def suggest(context: str, request: Request):
    """Generate suggested follow-up questions"""
    try:
        questions = await rag_instance.generate_questions(context)
        return questions
    except Exception as e:
        logger.error(f"Error suggesting questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))