from io import BytesIO
import os
from pathlib import Path
import tempfile
from typing import Any
import uuid

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
IMAGE_EXTENSIONS = {
    "GIF": ".gif",
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}
IMAGE_MIME_TYPES = {
    "GIF": "image/gif",
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def validated_image_metadata(content: bytes) -> tuple[str, str, int, int]:
    """Validate and inspect a bounded, decoded image."""
    if not content:
        raise HTTPException(status_code=400, detail="La imagen está vacía.")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="La imagen supera el límite de 10 MB.")

    try:
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
            image_format = image.format or ""
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=400,
                    detail="Las dimensiones de la imagen no son válidas.",
                )
            image.verify()
    except HTTPException:
        raise
    except (
        Image.DecompressionBombError,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida.") from exc

    extension = IMAGE_EXTENSIONS.get(image_format)
    mime_type = IMAGE_MIME_TYPES.get(image_format)
    if extension is None or mime_type is None:
        raise HTTPException(
            status_code=400,
            detail="Formato no permitido. Usa JPEG, PNG, WebP o GIF.",
        )
    return extension, mime_type, width, height


def validated_image_extension(content: bytes) -> str:
    """Keep the existing upload-validation contract for catalog uploads."""
    extension, _, _, _ = validated_image_metadata(content)
    return extension


def upload_root() -> Path:
    return Path(__file__).resolve().parents[2] / "static" / "uploads"


async def save_image_upload(file: UploadFile) -> dict[str, Any]:
    """Validate and atomically persist an image in the shared static volume."""
    try:
        content = await file.read(MAX_IMAGE_BYTES + 1)
        file_ext, mime_type, width, height = validated_image_metadata(content)
        file_name = f"{uuid.uuid4()}{file_ext}"

        upload_dir = upload_root()
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / file_name

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

        return {
            "url": f"/static/uploads/{file_name}",
            "storage_path": f"/static/uploads/{file_name}",
            "content_type": mime_type,
            "size_bytes": len(content),
            "width": width,
            "height": height,
            "file_name": file.filename or file_name,
            "file_path": str(file_path),
        }
    except HTTPException:
        raise
    except OSError as exc:
        raise HTTPException(status_code=500, detail="No fue posible guardar la imagen.") from exc
    finally:
        await file.close()
