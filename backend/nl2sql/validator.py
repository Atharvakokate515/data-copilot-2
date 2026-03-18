# backend/nl2sql/validator.py
import re

FORBIDDEN_KEYWORDS = ["drop", "alter", "truncate", "grant", "revoke"]

SAFE_SYSTEM_SCHEMAS = ["information_schema", "pg_catalog"]


def is_safe_sql(sql: str, allowed_tables: list[str]) -> dict:
    sql_lower = sql.lower().strip()

    # 1. Block forbidden keywords (word-boundary safe)
    for word in FORBIDDEN_KEYWORDS:
        if re.search(rf'\b{word}\b', sql_lower):
            return {"safe": False, "reason": f"Forbidden keyword detected: '{word}'"}

    # 2. Enforce WHERE on UPDATE / DELETE
    if re.match(r'^(update|delete)\b', sql_lower):
        if "where" not in sql_lower:
            return {"safe": False, "reason": "UPDATE/DELETE without WHERE is not allowed"}

    # 3. Allow system schema queries (information_schema, pg_catalog)
    if any(schema in sql_lower for schema in SAFE_SYSTEM_SCHEMAS):
        return {"safe": True}

    # 4. Allow scalar queries with no FROM clause (SELECT 1, SELECT now(), etc.)
    if "from" not in sql_lower:
        return {"safe": True}

    # 5. Check at least one known public table is referenced
    if not any(table in sql_lower for table in allowed_tables):
        return {"safe": False, "reason": "Query references unknown table"}

    return {"safe": True}