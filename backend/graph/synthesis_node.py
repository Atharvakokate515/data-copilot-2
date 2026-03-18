# backend/graph/synthesis_node.py

from llm.client import generate_text, llm
from llm.synthesis_prompt import SYNTHESIS_PROMPT

# ── REASONING LAYER (commented out) ──────────────────────────────
# Uncomment when upgrading to Claude or GPT-4.
# from llm.synthesis_prompt import REASONING_PROMPT
# from langchain_core.prompts import PromptTemplate
# import json
#
# def run_reasoning_layer(user_query, sql_results, rag_context):
#     prompt = PromptTemplate(
#         template=REASONING_PROMPT,
#         input_variables=["user_query", "sql_results", "rag_context"]
#     )
#     chain = prompt | llm
#     result = chain.invoke({"user_query": user_query, "sql_results": sql_results, "rag_context": rag_context})
#     raw = result.content if hasattr(result, "content") else str(result)
#     try:
#         return json.loads(raw.strip())
#     except Exception:
#         return None
# ─────────────────────────────────────────────────────────────────


def _format_sql_results(sql_results: list) -> str:
    if not sql_results:
        return "No SQL data available."
    return "\n".join(f"Task: {i['task']}\nResult: {i['result']}" for i in sql_results)


def _format_rag_results(rag_results: list) -> str:
    if not rag_results:
        return "No document context available."
    return "\n".join(f"Task: {i['task']}\nContext: {i['result']['answer']}" for i in rag_results)


def _extract_citations(rag_results: list) -> list[dict]:
    """
    Point 2 — Structured citations as list of dicts instead of a plain string.
    Each dict: {"source": str, "page": int, "confidence": float}
    Frontend can now render clickable links, page previews, confidence badges.
    """
    citations = []
    for item in rag_results:
        for c in item["result"].get("citations", []):
            citations.append({
                "source": c["source"],
                "page": c["page"],
                "confidence": round(1 - c["score"], 3)
            })
    return citations


def _format_citations_for_prompt(citations: list[dict]) -> str:
    if not citations:
        return "No citations available."
    return "\n".join(
        f"Source: {c['source']} | Page: {c['page']} | Confidence: {c['confidence']}"
        for c in citations
    )


def _is_answer_grounded(rag_results: list, citations: list[dict]) -> bool:
    """
    Point 4 — True if the answer is grounded in retrieved document evidence.
    Grounded = RAG was used AND at least one citation has confidence >= 0.5.
    If False, the LLM may have answered from general knowledge rather than
    your documents — frontend should warn the user accordingly.
    """
    if not rag_results or not citations:
        return False
    return any(c["confidence"] >= 0.5 for c in citations)


def synthesize_answer(state: dict) -> dict:

    user_query = state["user_input"]
    sql_results = state.get("sql_results", [])
    rag_results = state.get("rag_results", [])

    formatted_sql = _format_sql_results(sql_results)
    formatted_rag = _format_rag_results(rag_results)

    citations = _extract_citations(rag_results)                     # Point 2
    citations_for_prompt = _format_citations_for_prompt(citations)

    # ── REASONING LAYER HOOK (commented out) ─────────────────────
    # reasoning_output = None
    # if sql_results and rag_results:
    #     reasoning_output = run_reasoning_layer(user_query, formatted_sql, formatted_rag)
    # if reasoning_output:
    #     formatted_sql = f"Pre-analyzed metrics:\n{json.dumps(reasoning_output, indent=2)}"
    # ─────────────────────────────────────────────────────────────

    prompt = SYNTHESIS_PROMPT.format(
        user_query=user_query,
        sql_results=formatted_sql,
        rag_context=formatted_rag,
        citations=citations_for_prompt
    )

    response = generate_text(prompt).content

    return {
        "tool_result": {
            "tool": "synthesis",
            "answer": response,
            "sql_used": bool(sql_results),
            "rag_used": bool(rag_results),
            "citations": citations if citations else None,   # Point 2 — list of dicts
            "answer_grounded": _is_answer_grounded(rag_results, citations)  # Point 4
        }
    }