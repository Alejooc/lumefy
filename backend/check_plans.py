import sys
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.core.config import settings
from app.models.plan import Plan

async def check_plans():
    print(f"Connecting to DB...", flush=True)
    engine = create_async_engine(str(settings.DATABASE_URL))
    
    async with AsyncSession(engine) as session:
        print("Querying FREE plan...", flush=True)
        stmt = select(Plan).where(Plan.code == "FREE")
        result = await session.execute(stmt)
        plan = result.scalars().first()
        
        if plan:
            print(f"Found Plan: {plan.name} ({plan.code})", flush=True)
            print(f"Duration: {plan.duration_days} days", flush=True)
            print(f"Active: {plan.is_active}", flush=True)
        else:
            print("ERROR: Plan FREE not found!", flush=True)

    await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(check_plans())
    except Exception as e:
        print(f"Error: {e}", flush=True)
