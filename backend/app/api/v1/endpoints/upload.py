from typing import Any

from fastapi import APIRouter, UploadFile, File, Depends

from app.models.user import User
from app.core.permissions import PermissionChecker
from app.services.image_upload import (
    IMAGE_EXTENSIONS,
    MAX_IMAGE_BYTES,
    save_image_upload,
    validated_image_extension,
)

router = APIRouter()

async def _save_image_upload(file: UploadFile) -> dict[str, str]:
    """Preserve the catalog/logo upload endpoint while sharing validation."""
    response = await save_image_upload(file)
    return {"url": str(response["url"])}


@router.post("/", response_model=dict)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(PermissionChecker("manage_inventory")), # Or any authenticated user
) -> Any:
    """Upload a catalog image and return its URL."""
    return await _save_image_upload(file)


@router.post("/storefront-logo", response_model=dict)
async def upload_storefront_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, str]:
    """Upload a storefront logo for users who manage company branding."""
    return await _save_image_upload(file)
