from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from typing import Any
import shutil
import os
import uuid
from app.core.config import settings
from app.models.user import User
from app.core.permissions import PermissionChecker

router = APIRouter()

@router.post("/", response_model=dict)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(PermissionChecker("manage_inventory")), # Or any authenticated user
) -> Any:
    """
    Upload a file and return its URL.
    """
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Solo se permiten imágenes.")

        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        file_name = f"{uuid.uuid4()}{file_ext}"
        
        # Ensure upload directory exists
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "static", "uploads")
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        file_path = os.path.join(upload_dir, file_name)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Return URL
        # Assuming static is mounted at /static
        base_url = str(request.base_url)
        url = f"{base_url}static/uploads/{file_name}"
        
        return {"url": url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
