import psycopg2
import os

# Manual config since we want to avoid import issues
DB_NAME = "lumefy_db"
DB_USER = "postgres"
DB_PASS = "informake1144"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cur.fetchall()
    print("Tables found:", [t[0] for t in tables])
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {repr(e)}")
