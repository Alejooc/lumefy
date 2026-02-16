import sys
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.core.config import settings
from app.models.plan import Plan
from app.models.system_setting import SystemSetting

async def seed_data():
    print(f"Connecting to DB...")
    engine = create_async_engine(str(settings.DATABASE_URL))
    
    async with AsyncSession(engine) as session:
        # 1. Seed Plans
        print("Checking Plans...")
        result = await session.execute(select(Plan))
        plans = result.scalars().all()
        
        if not plans:
            print("Seeding Plans...")
            plans_data = [
                Plan(
                    name="Free Tier",
                    code="FREE",
                    price=0.0,
                    features={"users": 1, "branches": 1},
                    limits={"storage": "1GB"},
                    is_active=True,
                    is_public=True
                ),
                Plan(
                    name="Pro Plan",
                    code="PRO",
                    price=49.00,
                    features={"users": 5, "branches": 3, "pos": True},
                    limits={"storage": "10GB"},
                    is_active=True,
                    is_public=True
                ),
                Plan(
                    name="Enterprise",
                    code="ENTERPRISE",
                    price=199.00,
                    features={"users": 999, "branches": 999, "api": True},
                    limits={"storage": "1TB"},
                    is_active=True,
                    is_public=True
                )
            ]
            session.add_all(plans_data)
        else:
            print(f"Found {len(plans)} plans.")

        # 2. Seed Settings
        print("Checking Settings...")
        result = await session.execute(select(SystemSetting))
        settings_db = result.scalars().all()
        
        if not settings_db:
            print("Seeding Settings...")
            settings_data = [
                SystemSetting(key="system_name", value="Lumefy SaaS", group="branding", is_public=True),
                SystemSetting(key="primary_color", value="#4680ff", group="branding", is_public=True),
                SystemSetting(key="maintenance_mode", value="false", group="system", is_public=True)
            ]
            session.add_all(settings_data)
        else:
            print(f"Found {len(settings_db)} settings.")
            
        await session.commit()
        print("Seeding complete.")

    await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(seed_data())
    except Exception as e:
        print(f"Error: {e}")
