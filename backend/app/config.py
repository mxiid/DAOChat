import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    FAISS_INDEX_PATH = os.path.join(BASE_DIR, "data", "faiss_index")
    DOCUMENTS_PATH = os.path.join(BASE_DIR, "data")
