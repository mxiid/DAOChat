import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from urllib.parse import quote_plus

load_dotenv()

# Database configuration with default values
DB_USER = os.getenv('DB_USER', 'chatbot_user')
DB_PASSWORD = quote_plus(os.getenv('DB_PASSWORD', ''))
DB_HOST = os.getenv('DB_HOST', '195.35.0.107')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chatbot_db')

# Log configuration (but not sensitive data)
print(f"Connecting to database at {DB_HOST}:{DB_PORT}/{DB_NAME}")

# Create URL with encoded password
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 