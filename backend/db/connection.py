"""
Accept Postgres URL -- Create connection -- Fail loudly if invalid
"""

import psycopg2

def get_connection(db_url: str):
    return psycopg2.connect(db_url)

def test_connection(db_url: str):
    conn = get_connection(db_url)
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    cur.fetchone()
    cur.close()
    conn.close()
    return True
