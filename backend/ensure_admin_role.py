import asyncio
import os
import sys

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.role import Role
from app.models.company import Company # Added Import
from app.core import security
from sqlalchemy import select

async def ensure_admin_role():
    print("Connecting to DB...")
    async with SessionLocal() as db:
        try:
            # 1. Check for Admin Role
            result = await db.execute(select(Role).where(Role.name == "Admin"))
            role = result.scalars().first()
            
            if not role:
                print("Creating Admin Role...")
                role = Role(
                    name="Admin", 
                    description="Super Admin", 
                    permissions={"all": True}
                )
                db.add(role)
                await db.flush() # Get ID
            else:
                print(f"Admin Role found: {role.id}")
                # Ensure permissions are correct
                if not role.permissions or not role.permissions.get("all"):
                    print("Updating Admin Role permissions...")
                    role.permissions = {"all": True}
                    db.add(role)

            # 2. Check for Admin User
            result = await db.execute(select(User).where(User.email == "admin@lumefy.com"))
            user = result.scalars().first()
            
            if user:
                print(f"Admin User found: {user.email}")
                if user.role_id != role.id:
                    print(f"Assigning Admin Role to user... Old: {user.role_id} New: {role.id}")
                    user.role_id = role.id
                    db.add(user)
                    await db.commit()
                    print("Admin Role assigned successfully!")
                else:
                    print("User already has Admin Role.")
            else:
                print("Admin User NOT found. Ideally create it, but auth.py handles this in DEV mode.")
                # We can create it here too if needed
                
            await db.commit()
            
        except Exception as e:
            await db.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(ensure_admin_role())
