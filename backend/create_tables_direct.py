import psycopg2
import uuid

# Connection details matching fix_alembic.py
DB_NAME = "lumefy_db"
DB_USER = "postgres"
DB_PASS = "informake1144"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"

CREATE_PLANS_TABLE = """
CREATE TABLE IF NOT exists plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(255) NOT NULL UNIQUE,
    description VARCHAR,
    price FLOAT DEFAULT 0.0,
    currency VARCHAR(10) DEFAULT 'USD',
    duration_days INTEGER DEFAULT 30,
    features JSONB DEFAULT '{}',
    limits JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT TRUE
);
"""

CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT exists system_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    key VARCHAR(255) NOT NULL UNIQUE,
    value TEXT,
    "group" VARCHAR(255) DEFAULT 'general',
    is_public BOOLEAN DEFAULT FALSE,
    description VARCHAR
);
"""

try:
    print("Connecting to database...")
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    
    print("Creating plans table...")
    cur.execute(CREATE_PLANS_TABLE)
    
    print("Creating system_settings table...")
    cur.execute(CREATE_SETTINGS_TABLE)
    
    conn.commit()
    print("Tables created successfully!")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
