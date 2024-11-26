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
    # Drop schema and all tables
    connection.execute(text('DROP SCHEMA IF EXISTS chatbot CASCADE'))
    
    # Create schema and set permissions
    connection.execute(text('CREATE SCHEMA chatbot'))
    connection.execute(text(f'ALTER SCHEMA chatbot OWNER TO {DB_USER}'))
    connection.execute(text(f'GRANT ALL ON SCHEMA chatbot TO {DB_USER}'))

# Listen for schema creation
event.listen(Base.metadata, 'before_create', create_schema)

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

# Drop and recreate all tables
Base.metadata.drop_all(bind=sync_engine)
Base.metadata.create_all(bind=sync_engine)

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 