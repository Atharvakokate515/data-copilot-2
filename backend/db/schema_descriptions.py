# backend/db/schema_descriptions.py

from langchain_core.prompts import PromptTemplate
from llm.client import llm


SCHEMA_DESCRIPTION_PROMPT = """
You are a database documentation assistant.

Given the raw schema of a database (tables, columns, data types, primary keys, foreign keys, and sample rows),
write a plain-English description for each table and each of its columns.

Format your output EXACTLY like this, for every table:

Table: <table_name>
  Description: <one sentence describing what this table stores>
  Columns:
    - <column_name>: <one short phrase describing what this column stores>
    - ...

Do NOT add any extra text, headers, or explanations outside this format.

Raw Schema:
{schema}
"""

                                                                        #=====================================================
def generate_schema_descriptions(schema: str) -> str:                     #==================   PYDANTIC   ================
    """
    Calls the LLM to produce plain-English table and column descriptions
    appended to each section of the raw schema string.
    """

    prompt = PromptTemplate(
        template=SCHEMA_DESCRIPTION_PROMPT,
        input_variables=["schema"]
    )

    chain = prompt | llm

    result = chain.invoke({"schema": schema})

    # Extract string content from AIMessage
    if hasattr(result, "content"):
        return result.content.strip()

    return str(result).strip()
