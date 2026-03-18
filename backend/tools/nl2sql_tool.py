# backend/tools/nl2sql_tool.py
"""
Used exclusively by the Copilot agent graph (execution_node.py).
This tool is READ-ONLY — only SELECT queries are allowed.

INSERT / UPDATE / DELETE are intentionally blocked here.
Mutations are only permitted through the dedicated NL2SQL tab pipeline.
"""

from nl2sql.planner import plan_query
from nl2sql.generator import generate_sql
from nl2sql.validator import is_safe_sql
from db.executor import execute_sql
from db.schema import get_table_list


def nl2sql_tool(user_input: str, db_url: str):
    """
    Runs: planner → generator → SELECT guard → safety validator → executor

    Args:
        user_input : Analytics sub-task from the Copilot planner
        db_url     : Target database connection string
    """

    # ── Plan ──────────────────────────────────────────────────────
    plan = plan_query(user_input=user_input, db_url=db_url)

    # ── Generate SQL ──────────────────────────────────────────────
    sql= generate_sql(
        user_input=user_input,
        db_url=db_url,
        plan=plan
    )

    # ── Block non-SELECT queries ──────────────────────────────────
    # Copilot is an analytics/read-only assistant.
    # If the LLM ever generates a mutation query here, block it immediately.
    first_keyword = sql.strip().split()[0].upper() if sql.strip() else ""

    if first_keyword != "SELECT":
        return {
            "tool": "nl2sql",
            "success": False,
            "error": (
                f"Copilot nl2sql tool is read-only and only permits SELECT queries. "
                f"Got: {first_keyword}. Use the NL2SQL tab for data mutations."
            ),
            "sql": sql
        }

    # ── Safety validation ─────────────────────────────────────────
    tables = get_table_list(db_url)
    validation = is_safe_sql(sql, tables)

    if not validation["safe"]:
        return {
            "tool": "nl2sql",
            "success": False,
            "error": validation["reason"],
            "sql": sql
        }

    # ── Execute ───────────────────────────────────────────────────
    result = execute_sql(db_url, sql)

    return {
        "tool": "nl2sql",
        "success": True,
        "sql": sql,
        "execution": result
    }