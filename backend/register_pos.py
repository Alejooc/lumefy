import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.app_definition import AppDefinition

async def run():
    async with SessionLocal() as db:
        new_app = AppDefinition(
            slug="pos_module",
            name="Punto de Venta (POS)",
            description="Sistema de cobro rápido para mostrador, optimizado para lectores de código de barras e impresión de tickets.",
            category="Ventas",
            icon="feather icon-monitor"
        )
        db.add(new_app)
        await db.commit()
        print("POS App registered successfully")

if __name__ == "__main__":
    asyncio.run(run())
