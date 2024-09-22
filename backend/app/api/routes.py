from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List

from ..rag import RAG

router = APIRouter()
rag = RAG()

class Question(BaseModel):
    text: str

class DocumentLoad(BaseModel):
    directory_path: str

@router.post("/ask")
async def ask_question(question: Question):
    try:
        answer = rag.query(question.text)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/load_documents")
async def load_documents(doc_load: DocumentLoad, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(rag.add_texts, [doc_load.directory_path])
        return {"message": "Document loading started in the background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add more API routes as needed
