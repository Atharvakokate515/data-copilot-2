# backend/memory/models.py

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean
from datetime import datetime

Base = declarative_base()


# ─────────────────────────────────────────────────────────────────
# NL2SQL PIPELINE TABLES
# ─────────────────────────────────────────────────────────────────

class NL2SQLChatSession(Base):
    __tablename__ = "nl2sql_chat_sessions"
    id         = Column(String, primary_key=True)
    title      = Column(String, default="New NL2SQL Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NL2SQLChatMessage(Base):
    __tablename__ = "nl2sql_chat_messages"
    id         = Column(Integer, primary_key=True)
    session_id = Column(String, nullable=False)
    role       = Column(String, nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class NL2SQLSessionMeta(Base):
    __tablename__ = "nl2sql_session_meta"
    session_id = Column(String, primary_key=True)
    last_sql   = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────
# RAG COPILOT PIPELINE TABLES
# ─────────────────────────────────────────────────────────────────

class CopilotChatSession(Base):
    __tablename__ = "copilot_chat_sessions"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    title      = Column(String, default="New Copilot Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CopilotChatMessage(Base):
    __tablename__ = "copilot_chat_messages"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, nullable=False)
    role       = Column(String, nullable=False)
    content    = Column(Text, nullable=False)
    tool_used  = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────
# OBSERVABILITY TABLE
# ─────────────────────────────────────────────────────────────────

class RequestLog(Base):
    """
    One row per API request to either pipeline.
    Captures: endpoint, latency, tool used, SQL errors, retry flag.
    Used by GET /api/metrics to surface a dashboard.
    """
    __tablename__ = "request_logs"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    endpoint        = Column(String, nullable=False)        # "/api/chat-db" | "/api/agent-chat"
    pipeline        = Column(String, nullable=False)        # "nl2sql" | "copilot"
    latency_ms      = Column(Float, nullable=True)          # total request latency
    success         = Column(Boolean, nullable=True)
    stage_failed    = Column(String, nullable=True)         # "validation" | "execution" | None
    sql_error       = Column(Text, nullable=True)           # error string if execution failed
    was_retried     = Column(Boolean, default=False)        # True if SQL retry loop ran
    tool_used       = Column(String, nullable=True)         # "nl2sql" | "rag" | "chat" | "synthesis"
    query_type      = Column(String, nullable=True)         # "SELECT" | "UPDATE" etc
    created_at      = Column(DateTime, default=datetime.utcnow)