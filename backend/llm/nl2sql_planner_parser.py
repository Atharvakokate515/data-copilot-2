# backend/llm/nl2sql_planner_parser.py

from langchain_core.output_parsers import PydanticOutputParser
from core.nl2sql_plan_schema import NL2SQLPlan


nl2sql_planner_parser = PydanticOutputParser(pydantic_object=NL2SQLPlan)
