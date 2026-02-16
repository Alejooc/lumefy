import asyncio
import sys
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.system_setting import SystemSetting

async def check_broadcast():
    print("Connecting to DB...")
    async with SessionLocal() as db:
        query = select(SystemSetting).where(SystemSetting.key == "system_broadcast")
        result = await db.execute(query)
        setting = result.scalar_one_or_none()
        
        if setting:
            print(f"FOUND: Key={setting.key}")
            print(f"Value: {setting.value}")
            print(f"Company ID: {setting.company_id}")
            print(f"Is Public: {setting.is_public}")
        else:
            print("NOT FOUND: system_broadcast key is missing.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_broadcast())
