# backend/graph/planner_node.py

import logging

from llm.client import llm
from llm.planner_prompt import PLANNER_PROMPT
from llm.planner_parser import planner_parser
from core.planner_schema import PlannerOutput

from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)


def plan_tools(state: dict) -> dict:

    user_input = state["user_input"]

    prompt = PromptTemplate(
        template=PLANNER_PROMPT,
        input_variables=["user_input", "FORMAT_INSTRUCTIONS"]
    )

    chain = prompt | llm | planner_parser

    try:
        parsed_output: PlannerOutput = chain.invoke({
            "user_input": user_input,
            "FORMAT_INSTRUCTIONS": planner_parser.get_format_instructions()
        })

        # Guard: if a tool is listed but has no tasks, drop it and warn.
        # This catches cases where the LLM lists a tool but forgets its tasks.
        cleaned_tools = []

        for tool in parsed_output.tools:
            if tool == "nl2sql" and not parsed_output.sql_tasks:
                logger.warning(
                    "Planner listed 'nl2sql' but sql_tasks is empty for query: '%s'. "
                    "Dropping nl2sql from plan.", user_input
                )
                continue
            if tool == "rag" and not parsed_output.rag_tasks:
                logger.warning(
                    "Planner listed 'rag' but rag_tasks is empty for query: '%s'. "
                    "Dropping rag from plan.", user_input
                )
                continue
            cleaned_tools.append(tool)

        # If everything was dropped, fall back to chat
        if not cleaned_tools:
            logger.warning(
                "All planned tools dropped due to missing tasks for query: '%s'. "
                "Falling back to chat.", user_input
            )
            cleaned_tools = ["chat"]

        return {
            "planned_tools": cleaned_tools,
            "sql_tasks": parsed_output.sql_tasks or [],
            "rag_tasks": parsed_output.rag_tasks or []
        }

    except Exception as e:
        # Log the actual error — don't swallow it silently
        logger.error(
            "Planner failed to parse LLM output for query: '%s'. Error: %s. "
            "Falling back to chat.", user_input, str(e)
        )
        return {
            "planned_tools": ["chat"],
            "sql_tasks": [],
            "rag_tasks": []
        }


if __name__ == "__main__":
    test_cases = [
        "How many users signed up last month?",
        "What is our refund policy?",
        "How many orders were placed and what does our shipping policy say?",
        "Are we at risk of breaching any loan covenants this year?",
        "Hello, how are you?"
    ]

    for query in test_cases:
        print(f"\nQuery: {query}")
        result = plan_tools({"user_input": query})
        print(f"  Tools : {result['planned_tools']}")
        print(f"  SQL   : {result['sql_tasks']}")
        print(f"  RAG   : {result['rag_tasks']}")