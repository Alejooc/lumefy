from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import mimetypes
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.rate_limit import limiter
from app.core.middleware import MaintenanceMiddleware
import app.models # Import all models to ensure they are registered with SQLAlchemy
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.get("/healthz", tags=["health"])
async def liveness_probe():
    """Una sonda pública y mínima para Docker/orquestadores; no expone métricas."""
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
async def readiness_probe():
    """Verify that this API can serve requests, including its database."""
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return {"status": "ready"}

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Maintenance must be registered before CORS. FastAPI applies the most recently
# added middleware first, leaving CORS as the outer layer for 503 responses.
app.add_middleware(MaintenanceMiddleware)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_origin_regex=settings.BACKEND_CORS_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

from fastapi.staticfiles import StaticFiles
import os

# Ensure common image extensions are served with the expected MIME type in Docker/Alpine.
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("image/jpeg", ".jpg")
mimetypes.add_type("image/jpeg", ".jpeg")
mimetypes.add_type("image/png", ".png")

# Create static directory if it doesn't exist
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(api_router, prefix=settings.API_V1_STR)

