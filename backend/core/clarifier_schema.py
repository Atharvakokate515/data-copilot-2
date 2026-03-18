# backend/core/clarifier_schema.py

from pydantic import BaseModel, Field


class ClarifierOutput(BaseModel):

    is_clear: bool = Field(
        description="True if the user query is specific and complete enough to write SQL. False if it is ambiguous or missing key details."
    )
    question: str = Field(
        description="A follow-up question to ask the user when is_clear is False. Must be an empty string when is_clear is True."
    )
