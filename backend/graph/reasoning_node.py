# backend/graph/reasoning_node.py
"""
REASONING LAYER — Structured intermediate analysis between execution and synthesis.

PURPOSE:
For complex analytical queries (covenant breach detection, ratio vs threshold comparison,
trend analysis), the synthesizer alone with a small model like Llama-3.1-8B cannot
reliably extract metrics, match them to document thresholds, and produce accurate comparisons.

This node sits between execute_tools and synthesize_answer. It takes raw SQL rows and
RAG document text and produces a structured JSON with pre-extracted metrics, thresholds,
and comparison results. The synthesizer then works from this structured analysis instead
of raw unprocessed evidence.

HOW TO ENABLE:
1. In graph/graph.py: uncomment the reasoning node import and edges (instructions in that file)
2. In graph/synthesis_node.py: uncomment the reasoning layer hook block (instructions in that file)
3. In llm/synthesis_prompt.py: uncomment REASONING_PROMPT (already defined there)
4. Switch llm/client.py to use Claude Sonnet/Opus or GPT-4

WHEN IT HELPS:
- Queries that require comparing SQL figures against document thresholds
- Covenant / compliance / risk queries
- Queries requiring trend analysis across multiple SQL result sets
- Any query where the synthesizer currently gives vague or hallucinated answers

WHEN IT IS NOT NEEDED:
- Pure SQL queries (no RAG) — synthesizer handles fine
- Pure RAG queries (no SQL) — synthesizer handles fine
- Simple mixed queries where one result directly answers the question

NOTE: This node only activates meaningfully when both sql_results AND rag_results exist.
If only one type of evidence is present it passes state through unchanged.
"""

# ── Everything below is commented out. ───────────────────────────
# Uncomment the full block when you are ready to use this node.
# ─────────────────────────────────────────────────────────────────

# import json
# import logging
# from langchain_core.prompts import PromptTemplate
# from llm.client import llm
# from llm.synthesis_prompt import REASONING_PROMPT
#
# logger = logging.getLogger(__name__)
#
#
# def run_reasoning(state: dict) -> dict:
#     """
#     Intermediate reasoning node.
#
#     Takes:
#         state["sql_results"] : list of {task, result} dicts from execution node
#         state["rag_results"] : list of {task, result} dicts from execution node
#
#     Adds to state:
#         state["reasoning_output"] : structured JSON dict with metrics, thresholds,
#                                     comparisons, trend data, and missing data flags
#                                     OR None if reasoning failed / not applicable
#     """
#
#     sql_results = state.get("sql_results", [])
#     rag_results = state.get("rag_results", [])
#
#     # Only run reasoning when both SQL and RAG evidence exist.
#     # For single-tool results the synthesizer handles it fine directly.
#     if not sql_results or not rag_results:
#         return {"reasoning_output": None}
#
#     # Format evidence for the reasoning prompt
#     formatted_sql = "\n".join(
#         f"Task: {item['task']}\nResult: {item['result']}"
#         for item in sql_results
#     )
#     formatted_rag = "\n".join(
#         f"Task: {item['task']}\nContext: {item['result']['answer']}"
#         for item in rag_results
#     )
#
#     prompt = PromptTemplate(
#         template=REASONING_PROMPT,
#         input_variables=["user_query", "sql_results", "rag_context"]
#     )
#
#     chain = prompt | llm
#
#     try:
#         result = chain.invoke({
#             "user_query": state["user_input"],
#             "sql_results": formatted_sql,
#             "rag_context": formatted_rag
#         })
#
#         raw = result.content if hasattr(result, "content") else str(result)
#         # Strip markdown fences if the model wraps JSON in them
#         clean = raw.strip().replace("```json", "").replace("```", "").strip()
#         reasoning_output = json.loads(clean)
#
#         logger.info("Reasoning layer succeeded for query: '%s'", state["user_input"])
#         return {"reasoning_output": reasoning_output}
#
#     except Exception as e:
#         # If reasoning layer fails (bad JSON, timeout, etc.), log and continue.
#         # synthesize_answer will fall back to direct synthesis from raw evidence.
#         logger.warning(
#             "Reasoning layer failed for query: '%s'. Error: %s. "
#             "Falling through to direct synthesis.", state["user_input"], str(e)
#         )
#         return {"reasoning_output": None}