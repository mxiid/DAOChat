import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import asyncio

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
SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create schema if it doesn't exist
def create_schema(target, connection, **kw):
    # Create schema and set permissions
    connection.execute(text('CREATE SCHEMA IF NOT EXISTS chatbot'))
    connection.execute(text(f'ALTER SCHEMA chatbot OWNER TO {DB_USER}'))
    connection.execute(text(f'GRANT ALL ON SCHEMA chatbot TO {DB_USER}'))

# Migration script to add new columns
def add_new_columns(target, connection, **kw):
    # Add is_active column if it doesn't exist
    connection.execute(text("""
        DO $$ 
        BEGIN 
            BEGIN
                ALTER TABLE chatbot.chat_sessions 
                ADD COLUMN is_active BOOLEAN DEFAULT true;
            EXCEPTION
                WHEN duplicate_column THEN 
                    NULL;
            END;
        END $$;
    """))
    
    # Add ended_at column if it doesn't exist
    connection.execute(text("""
        DO $$ 
        BEGIN 
            BEGIN
                ALTER TABLE chatbot.chat_sessions 
                ADD COLUMN ended_at TIMESTAMP;
            EXCEPTION
                WHEN duplicate_column THEN 
                    NULL;
            END;
        END $$;
    """))
    
    # Add feedback columns to chat_messages if they don't exist
    connection.execute(text("""
        DO $$ 
        BEGIN 
            BEGIN
                ALTER TABLE chatbot.chat_messages 
                ADD COLUMN thumbs_up BOOLEAN,
                ADD COLUMN thumbs_down BOOLEAN,
                ADD COLUMN feedback_timestamp TIMESTAMP;
            EXCEPTION
                WHEN duplicate_column THEN 
                    NULL;
            END;
        END $$;
    """))

# Listen for schema creation and migration
event.listen(Base.metadata, 'before_create', create_schema)
event.listen(Base.metadata, 'after_create', add_new_columns)

# Create async engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=True
)

# Create sync engine for table creation
sync_engine = create_engine(
    SQLALCHEMY_DATABASE_URL.replace('+asyncpg', ''),
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

# Create async session factory
SessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Create tables if they don't exist (won't drop existing tables)
Base.metadata.create_all(bind=sync_engine)

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 