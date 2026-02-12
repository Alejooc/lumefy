import asyncio
from app.core.database import engine, Base
from app.models.plan import Plan
from app.models.system_setting import SystemSetting

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully")

if __name__ == "__main__":
    asyncio.run(create_tables())
