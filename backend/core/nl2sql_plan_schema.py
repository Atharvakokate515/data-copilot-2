# backend/core/nl2sql_schema.py

from pydantic import BaseModel, Field
from typing import List, Dict   #================    ======    ======================         ==========
                                #==========  ===  =============[ change name of the file ]============================
                                #=============    ====     ==================        =========================

class NL2SQLPlan(BaseModel):
    intent_summary: str = Field(
        description="Clear natural language explanation of what the user wants. If vague, add a note that clarification might be required."
    )
    metrics_requested: List[str] = Field(
        description="List of metrics or measures requested (e.g., 'total sales', 'average price')."
    )
    dimensions_requested: List[str] = Field(
        description="List of attributes or categories to group by or filter on (e.g., 'product line', 'customer name')."
    )
    filters_detected: List[str] = Field(
        description="Natural language descriptions of filtering conditions (e.g., 'orders from 2023', 'status is cancelled')."
    )
    aggregation_required: bool = Field(
        description="True ONLY if the user explicitly requests aggregation (sum, avg, count, total, etc.)."
    )
    grouping_conceptually_required: bool = Field(
        description="True ONLY if both an aggregation and a dimension exist."
    )
    sorting_requested: bool = Field(
        description="True ONLY if the user explicitly requests sorting or rankings (top, highest, lowest, order by, etc.)."
    )
    candidate_tables: List[str] = Field(
        description="List of likely relevant table names from the schema."
    )
    candidate_columns: Dict[str, List[str]] = Field(
        description="A mapping of table names to the likely relevant column names within those tables."
    )
