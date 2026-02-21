import asyncio
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.app_definition import AppDefinition
from sqlalchemy import select

async def update_pos_config():
    async with SessionLocal() as db:
        result = await db.execute(select(AppDefinition).where(AppDefinition.slug == "pos_module"))
        app_def = result.scalars().first()
        
        if app_def:
            # Set default settings for the App
            app_def.default_config = {
                "thermal_printer_paper": "80mm",
                "allow_negative_stock": False,
                "default_cash_drawer": "Main Register",
                "require_manager_for_void": True
            }
            
            # (Optional) Schema if the UI ever decides to render it beautifully in the future
            app_def.config_schema = {
                "type": "object",
                "properties": {
                    "thermal_printer_paper": {
                        "type": "string",
                        "title": "Tamaño de Papel",
                        "enum": ["80mm", "58mm"]
                    },
                    "allow_negative_stock": {
                        "type": "boolean",
                        "title": "Permitir ventas sin stock"
                    },
                    "default_cash_drawer": {
                        "type": "string",
                        "title": "Caja Registradora Predeterminada"
                    },
                    "require_manager_for_void": {
                        "type": "boolean",
                        "title": "Requerir clave para anular ventas"
                    }
                }
            }
            db.add(app_def)
            await db.commit()
            print("POS App Configuration Updated Successfully!")
        else:
            print("POS Module not found in DB!")

if __name__ == "__main__":
    asyncio.run(update_pos_config())
