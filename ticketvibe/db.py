import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    return psycopg2.connect(
        dbname="DB_Final",
        user="postgres",
        password="0000",
        host="localhost",
        port="5432"
    )

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    result = None
    try:
        cur.execute(query, params)
        if fetch_one:
            result = cur.fetchone()
        elif fetch_all:
            result = cur.fetchall()
        conn.commit()
    except Exception as e:
        print("Database error:", e)
    finally:
        cur.close()
        conn.close()
    return result


def execute_transaction(query, params=None, fetch_one=False, fetch_all=False):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    result = None
    try:
        conn.autocommit = False
        cur.execute(query, params)
        if fetch_one:
            result = cur.fetchone()
        elif fetch_all:
            result = cur.fetchall()
        print(result)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Database error:", e)
    finally:
        cur.close()
        conn.close()
    return result
