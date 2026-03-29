# backend/memory/chat_store.py
"""
DB-backed chat store for the RAG Copilot /agent-chat pipeline.

Uses:
  - copilot_chat_sessions  → one row per chat (integer ID)
  - copilot_chat_messages  → messages for that chat
"""

from .db import SessionLocal
from .models import CopilotChatSession, CopilotChatMessage


# ─────────────────────────────────────────────────────────────────
# Session management
# ─────────────────────────────────────────────────────────────────

def create_chat(title: str = "New Copilot Chat") -> int:
    db = SessionLocal()
    try:
        session = CopilotChatSession(title=title)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id
    finally:
        db.close()


def update_chat_title(chat_id: int, title: str) -> None:
    db = SessionLocal()
    try:
        row = db.query(CopilotChatSession).filter(
            CopilotChatSession.id == chat_id
        ).first()
        if row:
            row.title = title
            db.commit()
    finally:
        db.close()


def delete_copilot_chat(chat_id: int) -> bool:
    """
    Delete a Copilot session and all its messages.
    Returns True if the session existed and was deleted, False if not found.
    """
    db = SessionLocal()
    try:
        row = db.query(CopilotChatSession).filter(
            CopilotChatSession.id == chat_id
        ).first()
        if not row:
            return False

        # Cascade: messages → session
        db.query(CopilotChatMessage).filter(
            CopilotChatMessage.session_id == chat_id
        ).delete()
        db.delete(row)
        db.commit()
        return True
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# Message management
# ─────────────────────────────────────────────────────────────────

def save_message(chat_id: int, role: str, content: str, tool_used: str = None) -> None:
    db = SessionLocal()
    try:
        db.add(CopilotChatMessage(
            session_id=chat_id,
            role=role,
            content=content,
            tool_used=tool_used, 
        ))
        db.commit()
    finally:
        db.close()


def load_chat_history(chat_id: int, limit: int = 10) -> list[dict]:
    db = SessionLocal()
    try:
        rows = (
            db.query(CopilotChatMessage)
            .filter(CopilotChatMessage.session_id == chat_id)
            .order_by(CopilotChatMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        return [{"role": r.role, "content": r.content} for r in rows]
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# Session listing & restore
# ─────────────────────────────────────────────────────────────────

def list_copilot_sessions() -> list[dict]:
    db = SessionLocal()
    try:
        rows = (
            db.query(CopilotChatSession)
            .order_by(CopilotChatSession.updated_at.desc())
            .all()
        )
        return [
            {
                "chat_id": r.id,
                "title": r.title,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        db.close()


def get_copilot_session_by_id(chat_id: int) -> dict:
    """Return full session info including title for a given chat_id."""
    db = SessionLocal()
    try:
        row = db.query(CopilotChatSession).filter(
            CopilotChatSession.id == chat_id
        ).first()
        title = row.title if row else "Untitled"
    finally:
        db.close()

    history = load_chat_history(chat_id, limit=100)

    return {
        "chat_id": chat_id,
        "title": title,       # added — frontend needs this to populate workspace header on restore
        "messages": history,
    }