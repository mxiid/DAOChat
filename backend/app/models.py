from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Boolean, Text
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
    is_active = Column(Boolean, default=True)
    ended_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add relationship
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    session_feedback = relationship("SessionFeedback", back_populates="session", uselist=False)

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    __table_args__ = {'schema': 'chatbot'}
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey('chatbot.chat_sessions.id', ondelete='CASCADE'))
    role = Column(String)
    content = Column(String)
    tokens = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    message_metadata = Column(JSON, nullable=True)
    
    # Add feedback columns
    thumbs_up = Column(Boolean, nullable=True)
    thumbs_down = Column(Boolean, nullable=True)
    feedback_timestamp = Column(DateTime, nullable=True)
    
    # Add relationship
    session = relationship("ChatSession", back_populates="messages")

class SessionFeedback(Base):
    __tablename__ = 'session_feedback'
    __table_args__ = {'schema': 'chatbot'}
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey('chatbot.chat_sessions.id'))
    rating = Column(Integer)  # 1-5 rating
    feedback_text = Column(Text, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Add relationship
    session = relationship("ChatSession", back_populates="session_feedback")