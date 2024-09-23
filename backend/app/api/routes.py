from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..rag import RAG
import logging

router = APIRouter()
rag = RAG()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Question(BaseModel):
    text: str

class SuggestQuestionsRequest(BaseModel):
    context: str

@router.post("/ask")
async def ask_question(question: Question):
    try:
        logger.info(f"Received question: {question.text}")
        answer = await rag.query(question.text)
        logger.info(f"Generated answer: {answer}")
        return {"answer": answer}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.post("/suggest_questions")
async def suggest_questions(request: SuggestQuestionsRequest):
    try:
        logger.info(f"Received context for question suggestion: {request.context}")
        suggested_questions = await rag.generate_questions(request.context)  # Ensure this is awaited
        logger.info(f"Generated suggested questions: {suggested_questions}")
        return {"suggested_questions": suggested_questions}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in suggest_questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

def generate_questions(context: str) -> list[str]:
    # This is a placeholder function. In a real application, you would use
    # more sophisticated methods to generate relevant questions based on the context.
    # For now, we'll return some generic questions
    return [
        "Can you provide more details about this?",
        "How does this relate to DAO Proptech's investment strategy?",
        "What are the potential risks and benefits?",
        "Are there any similar projects or investments?"
    ]

