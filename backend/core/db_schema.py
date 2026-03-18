# backend/core/db_schema.py

from pydantic import BaseModel,Field
from typing import List


class SchemaOutput(BaseModel):

    sql: str = Field(description= "must contain ONLY the raw SQL code. No markdown code blocks, no preamble, and no explanation. If you add any text other than the query, the system will fail.")