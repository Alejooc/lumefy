import asyncio
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.notification_template import NotificationTemplate

async def seed_templates():
    async with SessionLocal() as db:
        templates = [
            {
                "code": "NEW_SALE",
                "name": "Nueva Venta (Admin)",
                "type": "success",
                "title_template": "Nueva Venta #{order_id}",
                "body_template": "Venta #{order_id} por ${amount} registrada por {user_name}",
                "is_active": True
            },
            {
                "code": "WELCOME",
                "name": "Bienvenida Usuario",
                "type": "info",
                "title_template": "¡Bienvenido a Lumefy!",
                "body_template": "Hola {user_name}, tu cuenta ha sido creada exitosamente.",
                "is_active": True
            },
            {
                "code": "LOW_STOCK",
                "name": "Alerta de Stock Bajo",
                "type": "warning",
                "title_template": "⚠️ Stock Bajo: {product_name}",
                "body_template": "El producto '{product_name}' ha llegado a su stock mínimo ({quantity} restantes).",
                "is_active": True
            }
        ]

        for t in templates:
            result = await db.execute(select(NotificationTemplate).where(NotificationTemplate.code == t["code"]))
            existing = result.scalars().first()
            
            if not existing:
                print(f"Creating template: {t['name']}")
                template = NotificationTemplate(**t)
                db.add(template)
            else:
                print(f"Template exists: {t['name']}")
        
        await db.commit()

if __name__ == "__main__":
    asyncio.run(seed_templates())
