import asyncio
import uuid
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.logistics import PackageType

DEFAULT_PACKAGES = [
    {"name": "Caja Pequeña", "width": 20.0, "height": 20.0, "length": 20.0, "max_weight": 5.0},
    {"name": "Caja Mediana", "width": 40.0, "height": 30.0, "length": 30.0, "max_weight": 15.0},
    {"name": "Caja Grande", "width": 60.0, "height": 40.0, "length": 40.0, "max_weight": 30.0},
    {"name": "Sobre A4", "width": 30.0, "height": 1.0, "length": 21.0, "max_weight": 0.5},
    {"name": "Pallet Estandar", "width": 120.0, "height": 100.0, "length": 100.0, "max_weight": 1000.0},
]

async def seed_package_types():
    async with SessionLocal() as session:
        # Check if empty
        result = await session.execute(select(PackageType))
        existing = result.scalars().all()
        
        if existing:
            print(f"Package types found: {[p.name for p in existing]}")
            return

        print("Seeding default package types...")
        for pkg in DEFAULT_PACKAGES:
            new_pkg = PackageType(
                name=pkg["name"],
                width=pkg["width"],
                height=pkg["height"],
                length=pkg["length"],
                max_weight=pkg["max_weight"],
                is_active=True
            )
            session.add(new_pkg)
        
        await session.commit()
        print("Success! Created 5 default package types.")

if __name__ == "__main__":
    asyncio.run(seed_package_types())
