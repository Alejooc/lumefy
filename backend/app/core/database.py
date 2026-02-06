from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Create Async Engine
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Create Session Factory
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

Base = declarative_base()

# Dependency
async def get_db():
    async with SessionLocal() as session:
        yield session
