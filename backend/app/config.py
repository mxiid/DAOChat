import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DOCUMENTS_PATH = os.getenv("DOCUMENTS_PATH", r"C:\Users\abdul\Downloads\DAO Proptech\DAOChat\data")
    FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "faiss_index")
