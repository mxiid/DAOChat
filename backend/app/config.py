import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT = int(os.getenv("MILVUS_PORT", 19530))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    # Add other configuration variables as needed
