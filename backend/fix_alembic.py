import psycopg2

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
    cur.execute("UPDATE alembic_version SET version_num = 'e0dd8d40bfef'")
    conn.commit()
    print("Successfully updated alembic_version to e0dd8d40bfef")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
