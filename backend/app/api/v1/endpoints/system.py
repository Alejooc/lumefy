from typing import Any, List, Dict
# Trigger reload for psutil installation
import psutil
import time
from fastapi import APIRouter, Depends, HTTPException
from app.core import auth
from app.models.user import User

router = APIRouter()

@router.get("/health", response_model=Any)
async def system_health(
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Get system health metrics (Super Admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    cpu_percent = psutil.cpu_percent(interval=None) # Non-blocking
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Uptime (boot time)
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    

    return {
        "cpu": {
            "percent": cpu_percent,
            "count": psutil.cpu_count()
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used
        },
        "disk": {
            "total": disk.total,
            "free": disk.free,
            "percent": disk.percent,
            "used": disk.used
        },
        "uptime_seconds": uptime_seconds
    }

from pydantic import BaseModel
from sqlalchemy import select
from app.models.system_setting import SystemSetting
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

class MaintenanceUpdate(BaseModel):
    enabled: bool

@router.get("/maintenance", response_model=MaintenanceUpdate)
async def get_maintenance_status(
    db: AsyncSession = Depends(get_db),
    # Public or restricted? Ideally public so Login page can show a banner, 
    # but the middleware allows /api/v1/admin and /login. 
    # Let's verify permission inside if needed, or make it open.
    # To manage it, we need admin. To view it, maybe open.
    # For now, stick to Admin Service using it, so require auth?
    # No, AdminService uses it.
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    result = await db.execute(select(SystemSetting.value).where(SystemSetting.key == "maintenance_mode"))
    mode_value = result.scalar_one_or_none()
    
    return {"enabled": mode_value == "true"}

@router.post("/maintenance", response_model=MaintenanceUpdate)
async def set_maintenance_mode(
    *,
    db: AsyncSession = Depends(get_db),
    status: MaintenanceUpdate,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    query = select(SystemSetting).where(SystemSetting.key == "maintenance_mode")
    result = await db.execute(query)
    setting = result.scalar_one_or_none()
    
    val_str = "true" if status.enabled else "false"
    
    if setting:
        setting.value = val_str
    else:
        setting = SystemSetting(key="maintenance_mode", value=val_str, group="system")
        db.add(setting)
        
    await db.commit()
    return {"enabled": status.enabled}

from sqlalchemy import text

@router.get("/database-stats", response_model=List[Dict[str, Any]])
async def get_database_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Get database statistics (Super Admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    # Query for table stats
    # We use pg_total_relation_size for total size (data + indexes)
    query = text("""
        SELECT 
            relname as table_name, 
            n_live_tup as row_count,
            pg_size_pretty(pg_total_relation_size(relid)) as total_size,
            pg_total_relation_size(relid) as total_size_bytes
        FROM pg_stat_user_tables 
        ORDER BY pg_total_relation_size(relid) DESC;
    """)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    stats = []
    for row in rows:
        stats.append({
            "table_name": row.table_name,
            "row_count": row.row_count,
            "total_size": row.total_size,
            "total_size_bytes": row.total_size_bytes
        })
        
    return stats

import json

class BroadcastMessage(BaseModel):
    message: str
    type: str = "info" # info, warning, danger, success
    is_active: bool = False

@router.get("/broadcast", response_model=BroadcastMessage)
async def get_broadcast_message(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    # Use text query to bypass any potential ORM-level tenant filtering
    # We want this to be visible to ALL users regardless of company_id
    query = text("SELECT value FROM system_settings WHERE key = 'system_broadcast'")
    result = await db.execute(query)
    value = result.scalar_one_or_none()
    
    if value:
        try:
            return json.loads(value)
        except:
            pass
            
    return {"message": "", "type": "info", "is_active": False}

@router.post("/broadcast", response_model=BroadcastMessage)
async def set_broadcast_message(
    *,
    db: AsyncSession = Depends(get_db),
    msg: BroadcastMessage,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    query = select(SystemSetting).where(SystemSetting.key == "system_broadcast")
    result = await db.execute(query)
    setting = result.scalar_one_or_none()
    
    value_json = json.dumps(msg.dict())
    
    if setting:
        setting.value = value_json
    else:
        setting = SystemSetting(key="system_broadcast", value=value_json, group="system")
        db.add(setting)
        
    await db.commit()
    return msg
