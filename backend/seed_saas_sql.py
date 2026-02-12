import psycopg2
import json

# Connection details
DB_NAME = "lumefy_db"
DB_USER = "postgres"
DB_PASS = "informake1144"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"

def seed():
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

        # 1. Seed Plans
        print("Checking Plans...")
        cur.execute("SELECT count(*) FROM plans")
        count = cur.fetchone()[0]
        
        if count == 0:
            print("Seeding Plans...")
            plans = [
                ("Free Tier", "FREE", 0.0, 30, json.dumps({"users": 1, "branches": 1}), json.dumps({"storage": "1GB"}), True, True),
                ("Pro Plan", "PRO", 49.00, 30, json.dumps({"users": 5, "branches": 3, "pos": True}), json.dumps({"storage": "10GB"}), True, True),
                ("Enterprise", "ENTERPRISE", 199.00, 30, json.dumps({"users": 999, "branches": 999, "api": True}), json.dumps({"storage": "1TB"}), True, True)
            ]
            
            insert_query = """
                INSERT INTO plans (name, code, price, duration_days, features, limits, is_active, is_public)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cur.executemany(insert_query, plans)
            print("Plans seeded.")
        else:
            print(f"Plans already exist ({count}).")

        # 2. Seed Settings
        print("Checking Settings...")
        cur.execute("SELECT count(*) FROM system_settings")
        count = cur.fetchone()[0]
        
        if count == 0:
            print("Seeding Settings...")
            settings = [
                ("system_name", "Lumefy SaaS", "branding", True),
                ("primary_color", "#4680ff", "branding", True),
                ("maintenance_mode", "false", "system", True)
            ]
            
            insert_query = """
                INSERT INTO system_settings (key, value, "group", is_public)
                VALUES (%s, %s, %s, %s)
            """
            
            cur.executemany(insert_query, settings)
            print("Settings seeded.")
        else:
             print(f"Settings already exist ({count}).")
             
        conn.commit()
        cur.close()
        conn.close()
        print("Done.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    seed()
