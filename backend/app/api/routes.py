from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..rag import RAG

router = APIRouter()
rag = RAG()

class Question(BaseModel):
    text: str

@router.post("/ask")
async def ask_question(question: Question):
    try:
        answer = rag.answer_question(question.text)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add more API routes as needed
