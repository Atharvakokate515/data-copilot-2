# backend/memory/session_store.py
"""
DB-backed session store for the NL2SQL /chat-db pipeline.

Uses:
  - nl2sql_chat_sessions   → one row per session (UUID)
  - nl2sql_chat_messages   → messages for that session
  - nl2sql_session_meta    → last_sql for follow-up context
"""
import uuid
from .db import SessionLocal
from .models import NL2SQLChatSession, NL2SQLChatMessage, NL2SQLSessionMeta


# ─────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────

def _get_or_create_session(db, session_id: str) -> NL2SQLChatSession:
    row = db.query(NL2SQLChatSession).filter(
        NL2SQLChatSession.id == session_id
    ).first()

    if not row:
        row = NL2SQLChatSession(id=session_id)
        db.add(row)
        meta = NL2SQLSessionMeta(session_id=session_id)
        db.add(meta)
        db.commit()
        db.refresh(row)

    return row


def _get_or_create_meta(db, session_id: str) -> NL2SQLSessionMeta:
    _get_or_create_session(db, session_id)
    meta = db.query(NL2SQLSessionMeta).filter(
        NL2SQLSessionMeta.session_id == session_id
    ).first()
    if not meta:
        meta = NL2SQLSessionMeta(session_id=session_id)
        db.add(meta)
        db.commit()
        db.refresh(meta)
    return meta


def create_session(title: str = "New NL2SQL Chat") -> str:
    """
    Create a new NL2SQL session with a server-generated UUID.
    Returns the new session_id string.

    This is the production-safe way to start a session — the server
    owns ID generation, never the client.
    """
    session_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        row = NL2SQLChatSession(id=session_id, title=title)
        db.add(row)
        meta = NL2SQLSessionMeta(session_id=session_id)
        db.add(meta)
        db.commit()
    finally:
        db.close()
    return session_id

# ─────────────────────────────────────────────────────────────────
# Public API — last_sql
# ─────────────────────────────────────────────────────────────────

def get_last_sql(session_id: str) -> str | None:
    db = SessionLocal()
    try:
        meta = db.query(NL2SQLSessionMeta).filter(
            NL2SQLSessionMeta.session_id == session_id
        ).first()
        return meta.last_sql if meta else None
    finally:
        db.close()


def update_last_sql(session_id: str, sql: str) -> None:
    db = SessionLocal()
    try:
        meta = _get_or_create_meta(db, session_id)
        meta.last_sql = sql
        db.commit()
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# Public API — messages
# ─────────────────────────────────────────────────────────────────

def get_chat_history(session_id: str, limit: int = 10) -> list[dict]:
    db = SessionLocal()
    try:
        messages = (
            db.query(NL2SQLChatMessage)
            .filter(NL2SQLChatMessage.session_id == session_id)
            .order_by(NL2SQLChatMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in messages]
    finally:
        db.close()


def append_message(session_id: str, role: str, content: str) -> None:
    db = SessionLocal()
    try:
        _get_or_create_session(db, session_id)
        db.add(NL2SQLChatMessage(session_id=session_id, role=role, content=content))
        db.commit()
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# Public API — session listing, restore, rename, delete
# ─────────────────────────────────────────────────────────────────

def list_nl2sql_sessions() -> list[dict]:
    db = SessionLocal()
    try:
        rows = (
            db.query(NL2SQLChatSession)
            .order_by(NL2SQLChatSession.updated_at.desc())
            .all()
        )
        return [
            {
                "session_id": r.id,
                "title": r.title,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        db.close()


def update_session_title(session_id: str, title: str) -> None:
    db = SessionLocal()
    try:
        row = db.query(NL2SQLChatSession).filter(
            NL2SQLChatSession.id == session_id
        ).first()
        if row:
            row.title = title
            db.commit()
    finally:
        db.close()


def delete_nl2sql_session(session_id: str) -> bool:
    """
    Delete an NL2SQL session and all its messages + meta.
    Returns True if the session existed and was deleted, False if not found.
    """
    db = SessionLocal()
    try:
        row = db.query(NL2SQLChatSession).filter(
            NL2SQLChatSession.id == session_id
        ).first()
        if not row:
            return False

        # Cascade: messages → meta → session
        db.query(NL2SQLChatMessage).filter(
            NL2SQLChatMessage.session_id == session_id
        ).delete()
        db.query(NL2SQLSessionMeta).filter(
            NL2SQLSessionMeta.session_id == session_id
        ).delete()
        db.delete(row)
        db.commit()
        return True
    finally:
        db.close()


def get_session_history_by_id(session_id: str) -> dict:
    """Return full session info including title for a given session_id."""
    db = SessionLocal()
    try:
        row = db.query(NL2SQLChatSession).filter(
            NL2SQLChatSession.id == session_id
        ).first()
        title = row.title if row else "Untitled"
    finally:
        db.close()

    last_sql = get_last_sql(session_id)
    history = get_chat_history(session_id, limit=100)

    return {
        "session_id": session_id,
        "title": title,
        "last_sql": last_sql,
        "chat_history": history,
    }