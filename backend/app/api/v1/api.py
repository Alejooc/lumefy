from fastapi import APIRouter
from app.api.v1.endpoints import (
    login, products, categories, inventory, pos, companies, reports, clients, users, roles
)

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(pos.router, prefix="/pos", tags=["pos"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
