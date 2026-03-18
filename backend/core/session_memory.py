# backend/core/session_memory.py

from typing import Dict, Any

SESSION_STORE: Dict[str, Dict[str, Any]] = {}


def get_session(session_id: str):

    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = {
            "chat_history": [],
            "last_sql": None
        }

    return SESSION_STORE[session_id]

###############
# maybe add pydantic to 'data' input here
def update_session(session_id: str, data: Dict[str, Any]):

    session = get_session(session_id)
    session.update(data)
