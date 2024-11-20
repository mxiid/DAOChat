from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    __table_args__ = {'schema': 'chatbot'}
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    session_metadata = Column(JSON, nullable=True)
    
    # Add relationship
    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    __table_args__ = {'schema': 'chatbot'}
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey('chatbot.chat_sessions.id'))
    role = Column(String)
    content = Column(String)
    tokens = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    message_metadata = Column(JSON, nullable=True)
    
    # Add relationship
    session = relationship("ChatSession", back_populates="messages") 