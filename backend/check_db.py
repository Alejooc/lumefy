import asyncio
import sys
from sqlalchemy import text
from app.core.database import engine

# Fix for Windows Asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def check_tables():
    try:
        async with engine.connect() as conn:
            print("Connected to database...")
            result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = result.fetchall()
            print("Tables found:", [t[0] for t in tables])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_tables())
