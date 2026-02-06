from fastapi import APIRouter
from app.api.v1.endpoints import login, products, categories, inventory

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
