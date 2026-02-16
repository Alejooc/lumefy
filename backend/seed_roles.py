import asyncio
import sys
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.company import Company
from app.models.role import Role

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DEFAULT_ROLE_TEMPLATES = [
    {
        "name": "ADMINISTRADOR",
        "description": "Administrador de empresa con control total del panel cliente.",
        "permissions": {"all": True}
    },
    {
        "name": "GERENTE",
        "description": "Gestion integral del negocio (sin funciones SaaS).",
        "permissions": {
            "view_dashboard": True,
            "manage_company": True,
            "manage_settings": True,
            "manage_users": True,
            "view_products": True,
            "manage_inventory": True,
            "view_inventory": True,
            "manage_clients": True,
            "create_sales": True,
            "view_sales": True,
            "manage_sales": True,
            "view_reports": True,
            "pos_access": True
        }
    },
    {
        "name": "VENTAS_POS",
        "description": "Operacion comercial diaria: clientes, POS y ventas.",
        "permissions": {
            "view_dashboard": True,
            "view_products": True,
            "manage_clients": True,
            "create_sales": True,
            "view_sales": True,
            "pos_access": True
        }
    },
    {
        "name": "LOGISTICA",
        "description": "Picking, packing, despacho y seguimiento de pedidos.",
        "permissions": {
            "view_dashboard": True,
            "view_sales": True,
            "manage_sales": True,
            "view_inventory": True
        }
    },
    {
        "name": "INVENTARIO_COMPRAS",
        "description": "Control de catalogo, compras e inventario.",
        "permissions": {
            "view_dashboard": True,
            "view_products": True,
            "manage_inventory": True,
            "view_inventory": True
        }
    },
    {
        "name": "REPORTES",
        "description": "Visualizacion de KPIs y reportes sin permisos de edicion.",
        "permissions": {
            "view_dashboard": True,
            "view_reports": True,
            "view_sales": True,
            "view_inventory": True
        }
    }
]


async def seed_roles() -> None:
    async with SessionLocal() as db:
        companies_result = await db.execute(select(Company))
        companies = companies_result.scalars().all()

        if not companies:
            print("No hay empresas. Crea una empresa primero y luego ejecuta seed_roles.py")
            return

        for company in companies:
            roles_result = await db.execute(select(Role).where(Role.company_id == company.id))
            current_roles = roles_result.scalars().all()
            existing_names = {role.name.strip().upper() for role in current_roles}

            print(f"Empresa: {company.name} ({company.id})")
            for template in DEFAULT_ROLE_TEMPLATES:
                role_name = template["name"].strip().upper()
                if role_name in existing_names:
                    print(f"  - {template['name']} ya existe")
                    continue

                db.add(
                    Role(
                        name=template["name"],
                        description=template["description"],
                        permissions=template["permissions"],
                        company_id=company.id
                    )
                )
                print(f"  + {template['name']} creado")

        await db.commit()
        print("Seed de roles completado.")


if __name__ == "__main__":
    asyncio.run(seed_roles())

