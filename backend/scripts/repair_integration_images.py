"""Repair legacy integration images that still point to provider URLs."""

import argparse
import asyncio
import json
from pathlib import Path
import sys
import uuid

# Allow both ``python scripts/...`` and ``python -m scripts...`` from the
# backend container's /app working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.services.integration_service import repair_external_integration_images


async def repair_images(source_id: uuid.UUID | None, dry_run: bool) -> dict[str, int]:
    async with SessionLocal() as db:
        stats = await repair_external_integration_images(
            db,
            source_id=source_id,
            dry_run=dry_run,
        )
        if not dry_run:
            await db.commit()
        return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Descarga al storage propio las imágenes de productos sincronizados."
    )
    parser.add_argument(
        "--source-id",
        type=uuid.UUID,
        help="Limita la reparación a una fuente de integración específica.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Cuenta las referencias externas sin descargar ni modificar registros.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = asyncio.run(repair_images(args.source_id, args.dry_run))
    print(json.dumps({"dry_run": args.dry_run, **result}, ensure_ascii=False, indent=2))
