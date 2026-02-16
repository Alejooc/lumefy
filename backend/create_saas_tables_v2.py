import sys
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.core.config import settings
from app.models.base import Base
# Import all models to ensure they are registered with Base
from app.models.user import User
from app.models.company import Company
from app.models.plan import Plan
from app.models.system_setting import SystemSetting

async def init_db():
    print(f"Connecting to {settings.DATABASE_URL}")
    engine = create_async_engine(str(settings.DATABASE_URL))
    
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
