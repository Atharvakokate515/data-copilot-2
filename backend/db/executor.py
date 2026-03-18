# backend/db/executor.py

import time
import psycopg2


def extract_table_name(sql: str) -> str | None:
    sql_lower = sql.lower()
    if "update" in sql_lower:
        return sql_lower.split("update")[1].split()[0]
    if "delete from" in sql_lower:
        return sql_lower.split("delete from")[1].split()[0]
    if "insert into" in sql_lower:
        return sql_lower.split("insert into")[1].split()[0]
    return None


def execute_sql(db_url: str, sql: str) -> dict:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    start_time = time.time()

    try:
        cur.execute(sql)
        query_type = sql.strip().split()[0].upper()

        if query_type == "SELECT":
            col_names = [desc[0] for desc in cur.description]   # added — required for frontend table headers
            data = cur.fetchall()
            result = {
                "type": "select",
                "col_names": col_names,
                "rows": [list(row) for row in data],            # list not tuple — JSON-safe
                "row_count": len(data),
            }
        else:
            conn.commit()
            rows_affected = cur.rowcount
            table_name = extract_table_name(sql)
            updated_rows = []

            if table_name:
                cur.execute(f"SELECT * FROM {table_name}")
                columns = [desc[0] for desc in cur.description]
                updated_rows = [dict(zip(columns, row)) for row in cur.fetchall()]

            result = {
                "type": "mutation",
                "rows_affected": rows_affected,
                "updated_table": updated_rows,
            }

        exec_time = round(time.time() - start_time, 4)
        return {
            "success": True,
            "query_type": query_type,
            "execution_time_sec": exec_time,
            "result": result,
        }

    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "error": str(e),
        }

    finally:
        cur.close()
        conn.close()