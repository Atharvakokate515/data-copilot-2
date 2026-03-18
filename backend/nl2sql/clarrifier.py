# backend/nl2sql/clarrifier.py

from langchain_core.prompts import PromptTemplate

from llm.client import llm
from llm.clarifier_prompt import CLARIFIER_PROMPT
from llm.clarifier_parser import clarifier_parser

from core.clarifier_schema import ClarifierOutput

from db.schema import get_schema


def _format_chat_history(history: list[dict]) -> str:
    if not history:
        return "No prior conversation."
    lines = []
    for msg in history:
        role = msg.get("role", "unknown").capitalize()
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def clarify_query(
    user_input: str,
    db_url: str,
    chat_history: list[dict] | None = None,
    last_sql: str | None = None
) -> ClarifierOutput:
    """
    Checks whether the user query is specific enough to generate SQL.

    Now accepts chat_history and last_sql so the clarifier can correctly
    judge follow-up queries as clear (even if they look vague in isolation).

    Returns:
        ClarifierOutput:
          - is_clear=True  → proceed to planner
          - is_clear=False → return clarification.question to the user
    """

    schema_summary = get_schema(db_url)

    prompt = PromptTemplate(
        template=CLARIFIER_PROMPT,
        input_variables=[
            "user_input",
            "schema_summary",
            "chat_history",
            "last_sql",
            "FORMAT_INSTRUCTIONS"
        ]
    )

    chain = prompt | llm | clarifier_parser

    result: ClarifierOutput = chain.invoke({
        "user_input": user_input,
        "schema_summary": schema_summary,
        "chat_history": _format_chat_history(chat_history or []),
        "last_sql": last_sql or "None",
        "FORMAT_INSTRUCTIONS": clarifier_parser.get_format_instructions()
    })

    return result


if __name__ == "__main__":
    print("── Clarifier Test ──")
    db_url = "postgresql://postgres:root@localhost:5432/classicmodels"

    # Test 1: standalone ambiguous query
    result = clarify_query(user_input="show me sales", db_url=db_url)
    print("Test 1 — standalone ambiguous:")
    print("  is_clear:", result.is_clear)
    print("  question:", result.question)

    # Test 2: follow-up that looks vague but has context
    history = [
        {"role": "user", "content": "show me total sales by product line"},
        {"role": "assistant", "content": "SELECT product_line, SUM(amount) FROM sales GROUP BY product_line"}
    ]
    result = clarify_query(
        user_input="now filter by Germany",
        db_url=db_url,
        chat_history=history,
        last_sql="SELECT product_line, SUM(amount) FROM sales GROUP BY product_line"
    )
    print("\nTest 2 — follow-up with context:")
    print("  is_clear:", result.is_clear)
    print("  question:", result.question)