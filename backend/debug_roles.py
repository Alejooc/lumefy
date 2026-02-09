import asyncio
import sys
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.role import Role

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def list_roles():
    async with SessionLocal() as db:
        result = await db.execute(select(Role))
        roles = result.scalars().all()
        for role in roles:
            print(f"Role: {role.name}, ID: {role.id}")

if __name__ == "__main__":
    asyncio.run(list_roles())
