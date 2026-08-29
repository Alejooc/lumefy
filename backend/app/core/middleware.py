import json
import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.system_setting import SystemSetting

logger = logging.getLogger(__name__)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _request_id(scope: dict) -> str:
    for name, value in scope.get("headers", []):
        if name.lower() == b"x-request-id":
            candidate = value.decode("ascii", errors="ignore")
            if REQUEST_ID_PATTERN.fullmatch(candidate):
                return candidate
            break
    return uuid4().hex


class RequestObservabilityMiddleware:
    """Attach a safe correlation ID and emit one structured completion event."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id(scope)
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            path = scope.get("path", "")
            if path not in {"/healthz", "/readyz", "/api/v1/healthz", "/api/v1/readyz"} or status_code >= 400:
                event = {
                    "event": "http_request_completed",
                    "request_id": request_id,
                    "method": scope.get("method"),
                    "path": path,
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                }
                logger.log(
                    logging.WARNING if status_code >= 500 else logging.INFO,
                    json.dumps(event, separators=(",", ":")),
                )


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
            path in {"/healthz", "/readyz", "/api/v1/healthz", "/api/v1/readyz"} or
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
        except Exception:
            # If DB fails, we probably shouldn't block everything unless intended.
            # But if DB is down, app is effectively down.
            logger.warning("Maintenance check failed", exc_info=True)

        return await call_next(request)
