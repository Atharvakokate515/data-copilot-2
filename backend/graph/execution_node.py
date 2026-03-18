# backend/graph/execution_node.py

from tools.nl2sql_tool import nl2sql_tool
from tools.rag_tool import rag_tool


def execute_tools(state: dict):

    planned_tools = state.get("planned_tools", [])

    sql_tasks = state.get("sql_tasks", [])
    rag_tasks = state.get("rag_tasks", [])

    db_url = state.get("db_url")
    chat_history = state.get("chat_history", [])

    sql_results = []
    rag_results = []

    # ---------- NL2SQL EXECUTION ----------

    if "nl2sql" in planned_tools:

        for task in sql_tasks:

            result = nl2sql_tool(
                user_input=task,
                db_url=db_url
            )

            sql_results.append({
                "task": task,
                "result": result
            })

    # ---------- RAG EXECUTION ----------

    if "rag" in planned_tools:

        for task in rag_tasks:

            result = rag_tool(
                user_input=task,
                chat_history=chat_history
            )

            rag_results.append({
                "task": task,
                "result": result
            })

    # ---------- CHAT FALLBACK ----------

    if planned_tools == ["chat"]:

        from tools.chat_tool import chat_tool

        chat_result = chat_tool(
            user_input=state["user_input"],
            chat_history=chat_history
        )

        return {
            "tool_result": chat_result
        }

    # ---------- RETURN EVIDENCE ----------

    return {
        "sql_results": sql_results,
        "rag_results": rag_results
    }
