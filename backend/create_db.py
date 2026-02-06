import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

# Get settings from env or use defaults
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "localhost")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
poster_db = "postgres"
target_db = os.getenv("POSTGRES_DB", "lumefy_db")

def create_database():
    try:
        # Connect to default postgres database
        print(f"Connecting to {POSTGRES_SERVER}...")
        conn = psycopg2.connect(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_SERVER,
            port=POSTGRES_PORT,
            dbname=poster_db
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if db exists
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{target_db}'")
        exists = cur.fetchone()
        
        if not exists:
            print(f"Creating database {target_db}...")
            cur.execute(f"CREATE DATABASE {target_db}")
            print(f"Database {target_db} created successfully!")
        else:
            print(f"Database {target_db} already exists.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")

if __name__ == "__main__":
    create_database()
