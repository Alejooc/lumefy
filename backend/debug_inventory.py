import asyncio
from app.core.database import SessionLocal
from app.models.user import User
from app.models.branch import Branch
from app.models.inventory import Inventory
from sqlalchemy import select

async def main():
    async with SessionLocal() as db:
        print("--- USERS ---")
        result = await db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f"User: {u.email}, Branch ID: {u.branch_id}")

        print("\n--- BRANCHES ---")
        result = await db.execute(select(Branch))
        branches = result.scalars().all()
        for b in branches:
            print(f"Branch: {b.name} (ID: {b.id})")

        print("\n--- INVENTORY (First 10) ---")
        result = await db.execute(select(Inventory).limit(10))
        inventory = result.scalars().all()
        for i in inventory:
            print(f"Product ID: {i.product_id}, Branch ID: {i.branch_id}, Qty: {i.quantity}")

if __name__ == "__main__":
    asyncio.run(main())
