import psycopg2

DB_NAME = "lumefy_db"
DB_USER = "postgres"
DB_PASS = "informake1144"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
cur = conn.cursor()

with open("backend/users_check.txt", "w") as f:
    f.write("=== ALL USERS ===\n")
    cur.execute("SELECT id, email, full_name, is_superuser, is_active, role_id, company_id FROM users ORDER BY email")
    cols = [desc[0] for desc in cur.description]
    f.write(f"Columns: {cols}\n\n")
    for row in cur.fetchall():
        f.write(f"  {row}\n")

cur.close()
conn.close()
print("Done. Check backend/users_check.txt")
