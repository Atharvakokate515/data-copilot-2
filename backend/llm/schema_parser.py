from langchain_core.output_parsers import PydanticOutputParser
from core.db_schema import SchemaOutput


schema_parser = PydanticOutputParser(
    pydantic_object=SchemaOutput
)
