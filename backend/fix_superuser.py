import psycopg2
from passlib.context import CryptContext

DB_NAME = "lumefy_db"
DB_USER = "postgres"
DB_PASS = "informake1144"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
cur = conn.cursor()

new_password = "admin123"
hashed = pwd_context.hash(new_password)

# Fix the superuser: clear company_id, reset password, ensure is_superuser
cur.execute("""
    UPDATE users 
    SET hashed_password = %s, 
        is_superuser = TRUE, 
        is_active = TRUE, 
        company_id = NULL,
        role_id = NULL,
        full_name = 'Super Admin'
    WHERE email = 'admin@lumefy.com'
""", (hashed,))

print(f"Updated {cur.rowcount} row(s)")
print(f"Email: admin@lumefy.com")
print(f"Password: {new_password}")

conn.commit()
cur.close()
conn.close()
print("Done!")
