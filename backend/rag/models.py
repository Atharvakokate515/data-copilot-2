# rag/models.py

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

Base = declarative_base()

class Chunk(Base):
    __tablename__ = "chunks"

    id         = Column(Integer, primary_key=True)
    chroma_id  = Column(String, unique=True)
    source     = Column(String)
    page       = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class Query(Base):
    __tablename__ = "queries"

    id         = Column(Integer, primary_key=True)
    query      = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
