import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from urllib.parse import quote_plus

load_dotenv()

# Create Base class first
Base = declarative_base()

# Database configuration
DB_USER = os.getenv('DB_USER', 'chatbot_user')
DB_PASSWORD = quote_plus(os.getenv('DB_PASSWORD', '@dm!n@123#'))
DB_HOST = os.getenv('DB_HOST', '195.35.0.107')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chatbot_db')

# Create URL with schema specification
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create schema if it doesn't exist
def create_schema(target, connection, **kw):
    # Create schema and set permissions
    connection.execute(text('CREATE SCHEMA IF NOT EXISTS chatbot'))
    connection.execute(text(f'ALTER SCHEMA chatbot OWNER TO {DB_USER}'))
    connection.execute(text(f'GRANT ALL ON SCHEMA chatbot TO {DB_USER}'))

# Listen for schema creation
event.listen(Base.metadata, 'before_create', create_schema)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={
        'options': '-c search_path=chatbot,public'  # Set schema search path
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 