from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import logging
from ..rag import ask_question, suggest_questions

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class Question(BaseModel):
    text: str

class Answer(BaseModel):
    text: str

@router.post("/ask", response_model=Answer)
async def ask(question: Question):
    try:
        answer = await ask_question(question.text)
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