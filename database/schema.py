from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
class DatasetMetadata(Base):
    __tablename__ = 'dataset_metadata'
    
    id = Column(Integer, primary_key=True)
    dataset_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(500))
    category = Column(String(100))
    description = Column(Text)
    endpoint = Column(String(500))
    fields = Column(JSON)
    record_count = Column(Integer)
    last_fetched = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
class EmbeddingMetadata(Base):
    __tablename__ = 'embedding_metadata'
    
    id = Column(Integer, primary_key=True)
    dataset_id = Column(String(100), nullable=False, index=True)
    chunk_id = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)
    meta_info = Column(JSON)
    embedding_model = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    return Session()

def get_db_session():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()
