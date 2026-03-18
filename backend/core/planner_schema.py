# backend/core/planner_schema.py

from pydantic import BaseModel, Field
from typing import List, Optional


class PlannerOutput(BaseModel):

    tools: List[str] = Field(
        description="List of tools to use. Valid values: 'nl2sql', 'rag', 'chat'."
    )
    sql_tasks: Optional[List[str]] = Field(
        default=[],
        description=(
            "List of READ-ONLY database analytics sub-tasks for the nl2sql tool. "
            "Each task must be answerable with a SELECT query only. "
            "Empty list if nl2sql is not needed."
        )
    )
    rag_tasks: Optional[List[str]] = Field(
        default=[],
        description=(
            "List of document retrieval sub-tasks for the rag tool. "
            "Empty list if rag is not needed."
        )
    )