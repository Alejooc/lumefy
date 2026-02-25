import asyncio
import os
import sys

from sqlalchemy import select

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.app_registry import APP_REGISTRY
from app.core.database import SessionLocal
from app.models.app_definition import AppDefinition


async def run() -> None:
    pos_def = next((app for app in APP_REGISTRY if app["slug"] == "pos_module"), None)
    if not pos_def:
        print("POS definition is missing from APP_REGISTRY.")
        return

    async with SessionLocal() as db:
        result = await db.execute(select(AppDefinition).where(AppDefinition.slug == "pos_module"))
        existing = result.scalars().first()

        if existing:
            print("POS App already exists. No changes applied.")
            return

        db.add(AppDefinition(**pos_def))
        await db.commit()
        print("POS App registered successfully.")


if __name__ == "__main__":
    asyncio.run(run())
