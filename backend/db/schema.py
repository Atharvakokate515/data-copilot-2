# backend/db/schema.py

import psycopg2


def get_schema(db_url: str) -> str:
    """
    Returns a rich schema string that includes:
    - Column names, data types
    - Primary keys
    - Foreign keys
    - 3 sample rows per table
    Used by the LLM prompts (planner, generator, clarifier).
    """
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # ── 1. Columns ────────────────────────────────────────────────
    cur.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """)
    col_rows = cur.fetchall()

    schema: dict = {}
    for table, column, dtype in col_rows:
        schema.setdefault(table, {"columns": [], "pk": [], "fk": [], "samples": []})
        schema[table]["columns"].append(f"{column} ({dtype})")

    # ── 2. Primary Keys ───────────────────────────────────────────
    cur.execute("""
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema    = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema    = 'public';
    """)
    for table, col in cur.fetchall():
        if table in schema:
            schema[table]["pk"].append(col)

    # ── 3. Foreign Keys ───────────────────────────────────────────
    cur.execute("""
        SELECT
            kcu.table_name,
            kcu.column_name,
            ccu.table_name  AS foreign_table,
            ccu.column_name AS foreign_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema    = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema    = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema    = 'public';
    """)
    for table, col, ftable, fcol in cur.fetchall():
        if table in schema:
            schema[table]["fk"].append(f"{col} → {ftable}.{fcol}")

    # ── 4. Sample Rows ────────────────────────────────────────────
    for table in schema:
        try:
            cur.execute(f'SELECT * FROM "{table}" LIMIT 3;')
            col_names = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            schema[table]["samples"] = [
                "  { " + ", ".join(f"{k}: {v}" for k, v in zip(col_names, row)) + " }"
                for row in rows
            ]
        except Exception:
            schema[table]["samples"] = []

    cur.close()
    conn.close()

    # ── 5. Build text ─────────────────────────────────────────────
    schema_text = ""
    for table, info in schema.items():
        schema_text += f"Table: {table}\n"
        if info["pk"]:
            schema_text += f"  Primary Key(s): {', '.join(info['pk'])}\n"
        if info["fk"]:
            schema_text += "  Foreign Keys:\n"
            for fk in info["fk"]:
                schema_text += f"    - {fk}\n"
        schema_text += "  Columns:\n"
        for col in info["columns"]:
            schema_text += f"    - {col}\n"
        if info["samples"]:
            schema_text += "  Sample Rows:\n"
            for s in info["samples"]:
                schema_text += f"{s}\n"
        schema_text += "\n"

    return schema_text.strip()


def get_table_list(db_url: str) -> list[str]:
    """Return list of public table names. Used by the SQL validator."""
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public';
    """)
    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tables


def get_schema_preview(db_url: str) -> tuple[list[dict], str]:
    """
    Return structured schema for the frontend workspace header / inspector,
    plus the database name.

    Returns: (tables, db_name)
      tables  — list of { name: str, columns: [str], pk: [str] }
      db_name — the connected database name (from SELECT current_database())

    Used by:
      POST /api/test-connection  — validates URL + returns tables for workspace init
      GET  /api/schema-preview   — live table list for workspace header
    """
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Database name
    cur.execute("SELECT current_database();")
    db_name = cur.fetchone()[0]

    # Columns
    cur.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """)
    raw: dict = {}
    for table, column, dtype in cur.fetchall():
        raw.setdefault(table, {"columns": [], "pk": []})
        raw[table]["columns"].append(f"{column} ({dtype})")

    # Primary keys
    cur.execute("""
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema    = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema    = 'public';
    """)
    for table, col in cur.fetchall():
        if table in raw:
            raw[table]["pk"].append(col)

    cur.close()
    conn.close()

    tables = [
        {"name": t, "columns": info["columns"], "pk": info["pk"]}
        for t, info in raw.items()
    ]
    return tables, db_name