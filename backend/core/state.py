# backend/core/state.py

from typing import TypedDict, Optional, Any


class AgentState(TypedDict):

    user_input: str
    db_url: Optional[str]

    planned_tools: Optional[list[str]]

    sql_tasks: Optional[list[str]]
    rag_tasks: Optional[list[str]]

    sql_results: Optional[list[Any]]
    rag_results: Optional[list[Any]]

    # ── REASONING LAYER (commented out) ──────────────────────────
    # Uncomment when enabling graph/reasoning_node.py.
    # This field carries the structured intermediate analysis
    # from the reasoning node to the synthesis node.
    #
    # reasoning_output: Optional[dict]
    # ─────────────────────────────────────────────────────────────

    tool_result: Optional[Any]

    chat_history: list[dict]