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
from app.core.config import settings
from sqlalchemy import select

async def ensure_admin_role():
    print("Connecting to DB...")
    async with SessionLocal() as db:
        try:
            admin_email = settings.FIRST_SUPERUSER
            admin_password = settings.FIRST_SUPERUSER_PASSWORD

            # 1. Ensure company exists
            result_company = await db.execute(select(Company).limit(1))
            company = result_company.scalars().first()
            if not company:
                print("Creating default company...")
                company = Company(
                    name="Lumefy Default Company",
                    currency="USD",
                    is_active=True
                )
                db.add(company)
                await db.flush()

            # 2. Check for Admin Role
            result = await db.execute(select(Role).where(Role.name == "Admin"))
            role = result.scalars().first()
            
            if not role:
                print("Creating Admin Role...")
                role = Role(
                    name="Admin", 
                    description="Super Admin", 
                    permissions={"all": True},
                    company_id=company.id
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

            # 3. Check for Admin User
            result = await db.execute(select(User).where(User.email == admin_email))
            user = result.scalars().first()
            
            if user:
                print(f"Admin User found: {user.email}")
                user.hashed_password = security.get_password_hash(admin_password)
                user.is_active = True
                user.is_superuser = True
                if not user.company_id:
                    user.company_id = company.id
                if user.role_id != role.id:
                    print(f"Assigning Admin Role to user... Old: {user.role_id} New: {role.id}")
                    user.role_id = role.id
                db.add(user)
                print("Admin user updated successfully.")
            else:
                print("Admin User NOT found. Creating admin user...")
                user = User(
                    email=admin_email,
                    full_name="Super Admin",
                    hashed_password=security.get_password_hash(admin_password),
                    is_active=True,
                    is_superuser=True,
                    company_id=company.id,
                    role_id=role.id
                )
                db.add(user)
                print("Admin user created successfully.")
                
            await db.commit()
            print(f"Admin credentials ready: {admin_email} / {admin_password}")
            
        except Exception as e:
            await db.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(ensure_admin_role())
