# backend/nl2sql/generator.py

from langchain_core.prompts import PromptTemplate

from llm.client import llm
from llm.schema_parser import schema_parser
from llm.nl2sql_prompts import NL2SQL_PROMPT

from core.nl2sql_plan_schema import NL2SQLPlan   # fixed: was "backend.core..." which breaks when run as a module

from db.schema import get_schema
from db.schema_descriptions import generate_schema_descriptions


def clean_sql(sql: str) -> str:
    sql = sql.replace("\\n", " ")
    sql = sql.replace("\n", " ")
    sql = sql.strip()
    return sql


def format_chat_history(history: list[dict]) -> str:
    """Convert list of {role, content} dicts to a readable string for the prompt."""
    if not history:
        return "No prior conversation."
    lines = []
    for msg in history:
        role = msg.get("role", "unknown").capitalize()
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def generate_sql(
    user_input: str,
    db_url: str,
    plan: NL2SQLPlan,
    last_sql: str | None = None,
    chat_history: list[dict] | None = None,
    error_feedback: str | None = None,     # set on retry: the execution error message
    failed_sql: str | None = None,         # set on retry: the SQL that caused the error
) -> str:
    """
    Generate a SQL query from a user's NL request, guided by a structured plan.

    Returns a single cleaned SQL string.

    On retry (error_feedback + failed_sql provided), uses NL2SQL_RETRY_PROMPT so the
    LLM sees its own mistake and the error message, which significantly improves
    correction accuracy.
    """

    raw_schema = get_schema(db_url)
    enriched_schema = generate_schema_descriptions(raw_schema)
    history_text = format_chat_history(chat_history or [])

    # ── Choose prompt: retry path vs normal path ──────────────────
    if error_feedback and failed_sql:
        from llm.nl2sql_prompts import NL2SQL_RETRY_PROMPT
        prompt = PromptTemplate(
            template=NL2SQL_RETRY_PROMPT,
            input_variables=[
                "user_input", "schema", "last_sql",
                "intent_summary", "metrics_requested", "dimensions_requested",
                "filters_detected", "aggregation_required", "grouping_conceptually_required",
                "sorting_requested", "candidate_tables", "candidate_columns",
                "chat_history", "FORMAT_INSTRUCTIONS",
                "failed_sql", "error_feedback",
            ]
        )
    else:
        prompt = PromptTemplate(
            template=NL2SQL_PROMPT,
            input_variables=[
                "user_input", "schema", "last_sql",
                "intent_summary", "metrics_requested", "dimensions_requested",
                "filters_detected", "aggregation_required", "grouping_conceptually_required",
                "sorting_requested", "candidate_tables", "candidate_columns",
                "chat_history", "FORMAT_INSTRUCTIONS",
            ]
        )

    chain = prompt | llm | schema_parser

    invoke_args = {
        "user_input": user_input,
        "schema": enriched_schema,
        "last_sql": last_sql or "None",
        "intent_summary": plan.intent_summary,
        "metrics_requested": ", ".join(plan.metrics_requested) if plan.metrics_requested else "None",
        "dimensions_requested": ", ".join(plan.dimensions_requested) if plan.dimensions_requested else "None",
        "filters_detected": ", ".join(plan.filters_detected) if plan.filters_detected else "None",
        "aggregation_required": plan.aggregation_required,
        "grouping_conceptually_required": plan.grouping_conceptually_required,
        "sorting_requested": plan.sorting_requested,
        "candidate_tables": ", ".join(plan.candidate_tables),
        "candidate_columns": str(plan.candidate_columns),
        "chat_history": history_text,
        "FORMAT_INSTRUCTIONS": schema_parser.get_format_instructions(),
    }

    if error_feedback and failed_sql:
        invoke_args["failed_sql"] = failed_sql
        invoke_args["error_feedback"] = error_feedback

    raw_output = chain.invoke(invoke_args)
    return clean_sql(raw_output.sql)


if __name__ == "__main__":
    from nl2sql.planner import plan_query

    print("── Generator Test ──")
    user_input = "how many tables are there"
    db_url = "postgresql://postgres:root@localhost:5432/classicmodels"

    plan = plan_query(user_input=user_input, db_url=db_url)

    print("==="*30)
    print("this is the plan intent   ---> ",plan.intent_summary)
    print("==="*30)
    print("this is the columns   ---> ",plan.candidate_columns)
    print("==="*30)
    print("this is the tables   ---> ",plan.candidate_tables)
    print("=="*40)
    sql = generate_sql(user_input=user_input, db_url=db_url, plan=plan)
    print("\nSQL:", sql)