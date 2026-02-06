from fastapi import APIRouter
from app.api.v1.endpoints import login, products

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
