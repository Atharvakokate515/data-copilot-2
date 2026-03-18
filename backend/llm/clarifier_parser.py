# backend/llm/clarifier_parser.py

from langchain_core.output_parsers import PydanticOutputParser
from core.clarifier_schema import ClarifierOutput


clarifier_parser = PydanticOutputParser(pydantic_object=ClarifierOutput)
