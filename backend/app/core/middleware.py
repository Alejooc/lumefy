from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.system_setting import SystemSetting

class MaintenanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Allow whitelisted paths (Login, Admin, Docs, Static)
        path = request.url.path
        if (
            path.startswith("/api/v1/login") or
            path.startswith("/api/v1/admin") or 
            path.startswith("/docs") or 
            path.startswith("/openapi.json") or
            path.startswith("/static") or
            request.method == "OPTIONS" # CORS preflight
        ):
            return await call_next(request)

        # 2. Check Maintenance Mode from DB
        # We create a specific session for this check to ensure we have fresh data
        # efficiently.
        try:
            async with SessionLocal() as db:
                result = await db.execute(
                    select(SystemSetting.value).where(SystemSetting.key == "maintenance_mode")
                )
                mode_value = result.scalar_one_or_none()
                
                is_maintenance = mode_value == "true"
                
                if is_maintenance:
                     return JSONResponse(
                        status_code=503,
                        content={
                            "detail": "System is currently under maintenance. Please try again later.",
                            "code": "MAINTENANCE_MODE"
                        }
                    )
        except Exception as e:
            # If DB fails, we probably shouldn't block everything unless intended.
            # But if DB is down, app is effectively down.
            import logging
            logging.getLogger(__name__).warning(f"Maintenance check failed: {e}")
            pass

        return await call_next(request)
