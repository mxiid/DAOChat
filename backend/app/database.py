import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import asyncio
from datetime import datetime

load_dotenv()

# Database configuration
DB_USER = os.getenv('DB_USER', 'chatbot_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', '@dm!n@123#')  # Use raw password, will be encoded later
DB_HOST = os.getenv('DB_HOST', '195.35.0.107')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chatbot_db')

# Create Base class
Base = declarative_base()

# Create URL with schema specification
SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create schema if it doesn't exist
def create_schema(target, connection, **kw):
    connection.execute(text('CREATE SCHEMA IF NOT EXISTS chatbot'))
    connection.execute(text(f'ALTER SCHEMA chatbot OWNER TO {DB_USER}'))
    connection.execute(text(f'GRANT ALL ON SCHEMA chatbot TO {DB_USER}'))

# Migration function to add last_activity column
def add_last_activity_column(connection):
    try:
        # Drop and recreate the table with the new column
        connection.execute(text("""
            DROP TABLE IF EXISTS chatbot.chat_sessions CASCADE;
            CREATE TABLE chatbot.chat_sessions (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                session_metadata JSONB,
                is_active BOOLEAN DEFAULT TRUE,
                ended_at TIMESTAMP WITHOUT TIME ZONE,
                last_activity TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
    except Exception as e:
        print(f"Error in migration: {str(e)}")
        raise

# Create sync engine for table creation and migration
sync_engine = create_engine(
    SQLALCHEMY_DATABASE_URL.replace('+asyncpg', ''),
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

# Execute schema creation and migration
with sync_engine.connect() as connection:
    create_schema(None, connection)
    add_last_activity_column(connection)
    connection.commit()

# Create async engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=True
)

# Create async session factory
SessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 