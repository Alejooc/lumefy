import asyncio
from sqlalchemy import text
from app.core.database import SessionLocal

async def check_enum():
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT unnest(enum_range(NULL::salestatus))"))
        print("Existing Enum Values:", result.scalars().all())

if __name__ == "__main__":
    asyncio.run(check_enum())
