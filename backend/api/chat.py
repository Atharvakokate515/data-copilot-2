# backend/api/chat.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

from nl2sql.clarrifier import clarify_query
from nl2sql.planner import plan_query
from nl2sql.generator import generate_sql
from nl2sql.validator import is_safe_sql

from db.executor import execute_sql
from db.schema import get_table_list, get_schema_preview
from db.connection import test_connection

from graph.graph import build_graph

from llm.client import generate_text
from llm.result_summary_prompt import RESULT_SUMMARY_PROMPT

from memory.chat_store import (
    create_chat, save_message, load_chat_history,
    list_copilot_sessions, get_copilot_session_by_id, update_chat_title,
    delete_copilot_chat,
)
from memory.session_store import (
    get_last_sql, update_last_sql, get_chat_history, append_message,
    get_session_history_by_id, list_nl2sql_sessions, update_session_title,
    delete_nl2sql_session, create_session,          # ← new import
)


router = APIRouter()
graph = build_graph()


# ─────────────────────────────────────────────────────────────────
# Request / response models
# ─────────────────────────────────────────────────────────────────

class NL2SQLRequest(BaseModel):
    db_url: str
    user_input: str
    session_id: str | None = None           # FIX 2: optional — server creates if absent
    clarification_response: str | None = None


class AgentChat(BaseModel):
    db_url: str
    user_input: str
    chat_id: int | None = None              # FIX 3: optional — server creates if absent


class CreateChatRequest(BaseModel):
    title: str = "New Copilot Chat"


class TestConnectionRequest(BaseModel):
    db_url: str


class RenameRequest(BaseModel):
    title: str


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _generate_result_summary(user_input: str, execution: dict) -> str:
    try:
        result = execution.get("result", {})
        prompt = RESULT_SUMMARY_PROMPT.format(
            user_input=user_input,
            rows=result.get("rows", [])[:10],
            row_count=result.get("row_count", 0),
        )
        response = generate_text(prompt)
        return response.content.strip() if hasattr(response, "content") else str(response).strip()
    except Exception:
        return ""


def _suggest_chart(execution: dict) -> dict | None:
    result = execution.get("result", {})
    if result.get("type") != "select":
        return None
    rows = result.get("rows", [])
    col_names = result.get("col_names", [])
    row_count = result.get("row_count", 0)
    if row_count == 0 or not rows:
        return None

    numeric_cols = [
        c for c in col_names
        if any(isinstance(row.get(c), (int, float)) for row in rows[:5])
    ]
    text_cols = [c for c in col_names if c not in numeric_cols]

    if row_count == 1 and len(col_names) == 1:
        return {"type": "table", "x_axis": None, "y_axis": None}
    if len(numeric_cols) >= 1 and len(text_cols) >= 1:
        chart_type = "pie" if row_count <= 6 and len(numeric_cols) == 1 else "bar"
        return {"type": chart_type, "x_axis": text_cols[0], "y_axis": numeric_cols[0]}
    if len(numeric_cols) >= 2:
        return {"type": "line", "x_axis": numeric_cols[0], "y_axis": numeric_cols[1]}
    return {"type": "table", "x_axis": None, "y_axis": None}


# ─────────────────────────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────────────────────────

@router.post("/test-connection")
def test_db_connection(data: TestConnectionRequest):
    try:
        test_connection(data.db_url)
        tables, db_name = get_schema_preview(data.db_url)
        return {"success": True, "db_name": db_name, "tables": tables, "error": None}
    except Exception as e:
        return {"success": False, "db_name": None, "tables": [], "error": str(e)}


@router.get("/schema-preview")
def schema_preview(db_url: str):
    try:
        tables, db_name = get_schema_preview(db_url)
        return {"success": True, "db_name": db_name, "tables": tables}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────────────────────────
# NL2SQL PIPELINE
# ─────────────────────────────────────────────────────────────────

@router.post("/chat-db")
def chat_with_db(data: NL2SQLRequest):

    # FIX 2: auto-create session if client didn't supply one
    session_id = data.session_id or create_session()
    is_new_session = data.session_id is None

    query = data.clarification_response or data.user_input
    last_sql = get_last_sql(session_id)
    chat_history = get_chat_history(session_id)

    # ── Clarifier ─────────────────────────────────────────────────
    if not data.clarification_response:
        clarification = clarify_query(
            user_input=query, db_url=data.db_url,
            chat_history=chat_history, last_sql=last_sql,
        )
        if not clarification.is_clear:
            append_message(session_id=session_id, role="user", content=data.user_input)
            append_message(session_id=session_id, role="assistant", content=clarification.question)
            return {
                "success": False,
                "session_id": session_id,           # always return session_id
                "is_new_session": is_new_session,
                "stage": "clarification",
                "error_code": "CLARIFICATION_NEEDED",
                "needs_clarification": True,
                "question": clarification.question,
            }

    if not chat_history:
        update_session_title(session_id, query[:60] + ("..." if len(query) > 60 else ""))

    # ── Planner ───────────────────────────────────────────────────
    plan = plan_query(user_input=query, db_url=data.db_url, chat_history=chat_history)

    # ── Generator ─────────────────────────────────────────────────
    sql = generate_sql(
        user_input=query, db_url=data.db_url,
        plan=plan, last_sql=last_sql, chat_history=chat_history,
    )

    # ── Validator (FIX 1: retry on validation failure instead of hard-failing) ──
    allowed_tables = get_table_list(data.db_url)
    validation = is_safe_sql(sql, allowed_tables)
    was_retried = False

    if not validation["safe"]:
        # The LLM produced invalid SQL — give it one chance to self-correct
        # using the validation failure reason as feedback, exactly like exec retry.
        original_sql = sql
        sql = generate_sql(
            user_input=query, db_url=data.db_url,
            plan=plan, last_sql=last_sql, chat_history=chat_history,
            error_feedback=f"Validation failed: {validation['reason']}",
            failed_sql=original_sql,
        )
        was_retried = True

        # Re-validate the corrected SQL — if it still fails, give up cleanly
        validation2 = is_safe_sql(sql, allowed_tables)
        if not validation2["safe"]:
            return {
                "success": False,
                "session_id": session_id,
                "is_new_session": is_new_session,
                "stage": "validation",
                "error_code": "VALIDATION_FAILED",
                "error": validation2["reason"],
                "generated_sql": sql,
                "original_sql": original_sql,
                "was_retried": True,
            }

    # ── Executor (with one retry on execution failure) ─────────────
    execution_result = execute_sql(data.db_url, sql)

    if not execution_result["success"]:
        error_msg = execution_result.get("error", "Unknown execution error")
        original_sql = sql

        sql = generate_sql(
            user_input=query, db_url=data.db_url,
            plan=plan, last_sql=last_sql, chat_history=chat_history,
            error_feedback=error_msg, failed_sql=original_sql,
        )
        was_retried = True

        # Re-validate before re-executing the corrected SQL
        validation_retry = is_safe_sql(sql, allowed_tables)
        if not validation_retry["safe"]:
            return {
                "success": False,
                "session_id": session_id,
                "is_new_session": is_new_session,
                "stage": "execution",
                "error_code": "RETRY_VALIDATION_FAILED",
                "error": validation_retry["reason"],
                "generated_sql": sql,
                "original_sql": original_sql,
                "was_retried": True,
            }

        execution_result = execute_sql(data.db_url, sql)

        if not execution_result["success"]:
            return {
                "success": False,
                "session_id": session_id,
                "is_new_session": is_new_session,
                "stage": "execution",
                "error_code": "RETRY_FAILED",
                "error": execution_result.get("error"),
                "generated_sql": sql,
                "original_sql": original_sql,
                "was_retried": True,
            }

    # ── Summary + chart (SELECT only) ────────────────────────────
    summary = ""
    chart_suggestion = None
    if execution_result.get("query_type") == "SELECT":
        summary = _generate_result_summary(query, execution_result)
        chart_suggestion = _suggest_chart(execution_result)

    # ── Persist ───────────────────────────────────────────────────
    append_message(session_id=session_id, role="user", content=query)
    append_message(session_id=session_id, role="assistant", content=sql)
    update_last_sql(session_id=session_id, sql=sql)

    return {
        "success": True,
        "session_id": session_id,               # always return — client must persist this
        "is_new_session": is_new_session,
        "stage": "complete",
        "generated_sql": sql,
        "summary": summary,
        "chart_suggestion": chart_suggestion,
        "was_retried": was_retried,
        "plan": {
            "intent": plan.intent_summary,
            "tables": plan.candidate_tables,
            "columns": plan.candidate_columns,
        },
        "execution": execution_result,
    }


# ── NL2SQL session management ─────────────────────────────────────

@router.post("/nl2sql-sessions")
def create_nl2sql_session():
    """
    Create a new NL2SQL session server-side and return its UUID.
    Frontend should call this before the first /chat-db message,
    then pass the returned session_id on all subsequent messages.
    """
    session_id = create_session()
    return {"success": True, "session_id": session_id}


@router.get("/nl2sql-sessions")
def get_nl2sql_sessions():
    return list_nl2sql_sessions()


@router.get("/session-history/{session_id}")
def get_session_history(session_id: str):
    return get_session_history_by_id(session_id)


@router.delete("/nl2sql-sessions/{session_id}")
def delete_nl2sql_session_endpoint(session_id: str):
    found = delete_nl2sql_session(session_id)
    if not found:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {"success": True, "session_id": session_id}


@router.patch("/nl2sql-sessions/{session_id}")
def rename_nl2sql_session(session_id: str, data: RenameRequest):
    update_session_title(session_id, data.title)
    return {"success": True, "session_id": session_id, "title": data.title}


# ─────────────────────────────────────────────────────────────────
# COPILOT PIPELINE
# ─────────────────────────────────────────────────────────────────

@router.post("/create-chat")
def create_new_chat(data: CreateChatRequest):
    chat_id = create_chat(title=data.title)
    return {"success": True, "chat_id": chat_id}


@router.post("/agent-chat")
def agent_chat(data: AgentChat):
    # FIX 3: auto-create chat if client didn't supply one
    is_new_chat = data.chat_id is None
    chat_id = data.chat_id if data.chat_id is not None else create_chat()

    history = load_chat_history(chat_id)

    if not history:
        update_chat_title(chat_id, data.user_input[:60] + ("..." if len(data.user_input) > 60 else ""))

    result = graph.invoke({
        "user_input": data.user_input,
        "db_url": data.db_url,
        "chat_history": history,
    })
    tool_result = result["tool_result"]

    save_message(chat_id=chat_id, role="user", content=data.user_input)
    save_message(chat_id=chat_id, role="assistant",
                 content=tool_result.get("answer", ""), tool_used=tool_result.get("tool"))

    return {
        "success": True,
        "chat_id": chat_id,                 # always return — client must persist this
        "is_new_chat": is_new_chat,
        "response": tool_result,
    }


# ── Copilot session management ────────────────────────────────────

@router.get("/copilot-sessions")
def get_copilot_sessions():
    return list_copilot_sessions()


@router.get("/copilot-history/{chat_id}")
def get_copilot_history(chat_id: int):
    return get_copilot_session_by_id(chat_id)


@router.delete("/copilot-sessions/{chat_id}")
def delete_copilot_session_endpoint(chat_id: int):
    found = delete_copilot_chat(chat_id)
    if not found:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found.")
    return {"success": True, "chat_id": chat_id}


@router.patch("/copilot-sessions/{chat_id}")
def rename_copilot_session(chat_id: int, data: RenameRequest):
    update_chat_title(chat_id, data.title)
    return {"success": True, "chat_id": chat_id, "title": data.title}