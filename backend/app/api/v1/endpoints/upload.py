from io import BytesIO
import os
from pathlib import Path
import tempfile
from typing import Any
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from PIL import Image, UnidentifiedImageError

from app.models.user import User
from app.core.permissions import PermissionChecker

router = APIRouter()

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
IMAGE_EXTENSIONS = {
    "GIF": ".gif",
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}


def validated_image_extension(content: bytes) -> str:
    """Return a server-controlled extension for a bounded, decoded image."""
    if not content:
        raise HTTPException(status_code=400, detail="La imagen está vacía.")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="La imagen supera el límite de 10 MB.")

    try:
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
            image_format = image.format
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=400,
                    detail="Las dimensiones de la imagen no son válidas.",
                )
            image.verify()
    except (
        Image.DecompressionBombError,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida.") from exc

    extension = IMAGE_EXTENSIONS.get(image_format or "")
    if extension is None:
        raise HTTPException(
            status_code=400,
            detail="Formato no permitido. Usa JPEG, PNG, WebP o GIF.",
        )
    return extension

async def _save_image_upload(file: UploadFile) -> dict[str, str]:
    """Validate and persist an image in the shared static asset volume."""
    try:
        content = await file.read(MAX_IMAGE_BYTES + 1)
        file_ext = validated_image_extension(content)
        file_name = f"{uuid.uuid4()}{file_ext}"
        
        upload_dir = Path(__file__).resolve().parents[4] / "static" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / file_name

        # Write atomically so an interrupted request cannot leave a partial asset.
        descriptor, temporary_path = tempfile.mkstemp(prefix=".upload-", dir=upload_dir)
        try:
            with os.fdopen(descriptor, "wb") as buffer:
                buffer.write(content)
                buffer.flush()
                os.fsync(buffer.fileno())
            os.replace(temporary_path, file_path)
        except Exception:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise
            
        # A root-relative URL preserves HTTPS on admin and storefront domains.
        return {"url": f"/static/uploads/{file_name}"}
    except HTTPException:
        raise
    except OSError as exc:
        raise HTTPException(status_code=500, detail="No fue posible guardar la imagen.") from exc
    finally:
        await file.close()


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
