import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import asyncio
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

# Database configuration
DB_USER = os.getenv('DB_USER', 'chatbot_user')
DB_PASSWORD = quote_plus(os.getenv('DB_PASSWORD', '@dm!n@123#'))
DB_HOST = os.getenv('DB_HOST', '195.35.0.107')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chatbot_db')

# Force drop and recreate schema using psycopg2
def force_drop_schema():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD.replace('%40', '@'),  # Fix encoded characters
        host=DB_HOST,
        port=DB_PORT
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    # Force disconnect all other clients
    cur.execute("""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = %s
        AND pid <> pg_backend_pid()
    """, [DB_NAME])
    
    # Drop and recreate schema
    cur.execute("DROP SCHEMA IF EXISTS chatbot CASCADE")
    cur.execute("CREATE SCHEMA chatbot")
    cur.execute(f"ALTER SCHEMA chatbot OWNER TO {DB_USER}")
    cur.execute(f"GRANT ALL ON SCHEMA chatbot TO {DB_USER}")
    
    cur.close()
    conn.close()

# Force recreate schema
force_drop_schema()

# Create Base class
Base = declarative_base()

# Create URL with schema specification
SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create schema if it doesn't exist
def create_schema(target, connection, **kw):
    connection.execute(text('CREATE SCHEMA IF NOT EXISTS chatbot'))
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

# Create tables
Base.metadata.create_all(bind=sync_engine)

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 