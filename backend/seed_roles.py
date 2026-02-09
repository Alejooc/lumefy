import asyncio
import sys
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.role import Role
from app.models.company import Company
from app.models.user import User

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def seed_roles():
    async with SessionLocal() as db:
        roles = [
            {"name": "ADMIN", "description": "Administrator with full access", "permissions": {"all": True}},
            {"name": "MANAGER", "description": "Store Manager", "permissions": {"manage_users": True, "manage_inventory": True, "view_reports": True}},
            {"name": "CASHIER", "description": "Cashier for POS", "permissions": {"pos_access": True, "view_products": True}}
        ]
        
        for role_data in roles:
            result = await db.execute(select(Role).where(Role.name == role_data["name"]))
            existing_role = result.scalars().first()
            
            if not existing_role:
                new_role = Role(**role_data)
                db.add(new_role)
                print(f"Role {role_data['name']} created.")
            else:
                print(f"Role {role_data['name']} already exists.")
        
        await db.commit()

if __name__ == "__main__":
    asyncio.run(seed_roles())
