# backend/tools/chat_tool.py
"""
General conversation fallback tool for the Copilot pipeline.
Used when the planner determines the query needs neither database nor documents —
greetings, small talk, general questions the LLM can answer from its own knowledge.

Everything is self-contained in this file: prompt, schema, parser, and tool function.
"""

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from llm.client import llm



class ChatOutput(BaseModel):
    answer: str = Field(
        description="A helpful, conversational response to the user's message."
    )

chat_parser = PydanticOutputParser(pydantic_object=ChatOutput)


CHAT_PROMPT = """
You are a helpful enterprise data copilot assistant.
The user's message does not require database queries or document retrieval.
Respond in a friendly, concise, and professional tone.
Use the conversation history below for context if the user is referring to something prior.

Conversation History:
{chat_history}

User Message:
{user_input}

{FORMAT_INSTRUCTIONS}
"""



def _format_history(chat_history: list[dict]) -> str:
    if not chat_history:
        return "No prior conversation."
    lines = []
    for msg in chat_history:
        role = msg.get("role", "unknown").capitalize()
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# Tool function
# ─────────────────────────────────────────────────────────────────

def chat_tool(user_input: str, chat_history: list[dict] = None) -> dict:
    """
    General conversation fallback.

    Args:
        user_input   : The user's message
        chat_history : Recent conversation messages for context

    Returns:
        dict with tool, answer keys — matches what execution_node and
        synthesis_node expect from all tool results.
    """

    chat_history = chat_history or []

    prompt = PromptTemplate(
        template=CHAT_PROMPT,
        input_variables=["user_input", "chat_history", "FORMAT_INSTRUCTIONS"]
    )

    chain = prompt | llm | chat_parser

    try:
        result: ChatOutput = chain.invoke({
            "user_input": user_input,
            "chat_history": _format_history(chat_history),
            "FORMAT_INSTRUCTIONS": chat_parser.get_format_instructions()
        })
        answer = result.answer

    except Exception:
        # If parsing fails, fall back to raw LLM call without Pydantic
        raw = llm.invoke(
            CHAT_PROMPT.format(
                user_input=user_input,
                chat_history=_format_history(chat_history),
                FORMAT_INSTRUCTIONS=""
            )
        )
        answer = raw.content if hasattr(raw, "content") else str(raw)

    return {
        "tool": "chat",
        "answer": answer
    }