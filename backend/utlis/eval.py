# backend/utils/eval.py
"""
Accuracy evaluation utilities for both pipelines.

NL2SQL:  executability, non-empty result, query type match
Copilot: answer grounding, faithfulness proxy (n-gram overlap), citation score

Intentionally lightweight — no extra LLM calls.
"""


# ─────────────────────────────────────────────────────────────────
# NL2SQL evaluation
# ─────────────────────────────────────────────────────────────────

def evaluate_sql_result(
    execution_result: dict,
    expected_query_type: str | None = None
) -> dict:
    """
    Evaluate execute_sql() output.

    Returns:
        executable        : SQL ran without error
        returned_rows     : SELECT returned >= 1 row
        query_type_match  : matches expected type if provided
        was_retried       : retry loop ran
        score             : 0.0 – 1.0 composite
    """
    executable  = execution_result.get("success", False)
    was_retried = execution_result.get("was_retried", False)
    query_type  = execution_result.get("query_type", "")
    result      = execution_result.get("result", {})

    returned_rows = (
        executable
        and result.get("type") == "select"
        and result.get("row_count", 0) > 0
    )

    type_match = (
        query_type.upper() == expected_query_type.upper()
        if expected_query_type else True
    )

    score = round(sum([executable, returned_rows, type_match]) / 3, 3)

    return {
        "executable":       executable,
        "returned_rows":    returned_rows,
        "query_type_match": type_match,
        "was_retried":      was_retried,
        "score":            score
    }


# ─────────────────────────────────────────────────────────────────
# RAG / Copilot evaluation
# ─────────────────────────────────────────────────────────────────

def evaluate_rag_answer(
    answer: str,
    citations: list[dict] | None,
    rag_results: list[dict] | None
) -> dict:
    """
    Evaluate synthesize_answer() output for RAG responses.

    Faithfulness proxy: checks for 5-word overlap between retrieved
    chunks and the answer — fast hallucination signal, no LLM needed.

    Returns:
        answer_grounded    : any citation confidence >= 0.5
        faithfulness_proxy : answer contains phrases from retrieved chunks
        grounding_score    : highest citation confidence
        citation_count     : number of citations returned
        score              : 0.0 – 1.0 composite
    """
    citations   = citations or []
    rag_results = rag_results or []

    answer_grounded = any(c.get("confidence", 0) >= 0.5 for c in citations)
    grounding_score = max((c.get("confidence", 0) for c in citations), default=0.0)

    # 5-gram overlap between retrieved chunks and the answer
    faithfulness = False
    answer_lower = answer.lower()
    for item in rag_results:
        words = item.get("result", {}).get("answer", "").lower().split()
        for i in range(len(words) - 4):
            if " ".join(words[i:i + 5]) in answer_lower:
                faithfulness = True
                break
        if faithfulness:
            break

    score = round(sum([answer_grounded, faithfulness]) / 2, 3)

    return {
        "answer_grounded":    answer_grounded,
        "faithfulness_proxy": faithfulness,
        "grounding_score":    round(grounding_score, 3),
        "citation_count":     len(citations),
        "score":              score
    }


# ─────────────────────────────────────────────────────────────────
# Top-level dispatcher
# ─────────────────────────────────────────────────────────────────

def evaluate_pipeline_response(response: dict, pipeline: str) -> dict:
    """
    Called after either pipeline returns a response.
    pipeline: "nl2sql" | "copilot"
    """
    if pipeline == "nl2sql":
        return {"pipeline": "nl2sql", **evaluate_sql_result(response.get("execution", {}))}

    if pipeline == "copilot":
        tool_result = response.get("response", {})
        return {
            "pipeline": "copilot",
            **evaluate_rag_answer(
                answer=tool_result.get("answer", ""),
                citations=tool_result.get("citations"),
                rag_results=[]
            )
        }

    return {"pipeline": pipeline, "score": None}