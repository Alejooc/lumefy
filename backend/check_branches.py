import asyncio
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.branch import Branch
from app.models.company import Company
import uuid

async def main():
    async with SessionLocal() as db:
        # Check for any branch
        result = await db.execute(select(Branch))
        branches = result.scalars().all()
        
        if branches:
            print(f"Found branches: {[b.id for b in branches]}")
            for b in branches:
                print(f"Branch: {b.name} (ID: {b.id})")
        else:
            print("No branches found. Creating default branch...")
            # Check for company
            result_company = await db.execute(select(Company))
            company = result_company.scalars().first()
            
            company_id = company.id if company else None
            
            if not company_id:
                # Create default company if missing (shouldn't happen if user exists, but just in case)
                print("No company found. Creating default company...")
                new_company = Company(name="Default Company")
                db.add(new_company)
                await db.flush()
                await db.refresh(new_company)
                company_id = new_company.id
            
            new_branch = Branch(
                name="Sucursal Principal",
                company_id=company_id,
                is_warehouse=True,
                allow_pos=True
            )
            db.add(new_branch)
            await db.commit()
            print(f"Created Branch: {new_branch.name} (ID: {new_branch.id})")

if __name__ == "__main__":
    asyncio.run(main())
