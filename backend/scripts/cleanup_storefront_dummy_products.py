import argparse
import asyncio

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.models.product import Product
from app.models.storefront import PublishedProduct, StoreCollectionProduct, Storefront


async def cleanup_dummy_products(subdomain: str, dry_run: bool) -> None:
    async with SessionLocal() as db:
        storefront_result = await db.execute(
            select(Storefront).where(Storefront.subdomain == subdomain)
        )
        storefront = storefront_result.scalars().first()
        if not storefront:
            raise RuntimeError(f"No se encontro un storefront para '{subdomain}'.")

        published_result = await db.execute(
            select(PublishedProduct.id, PublishedProduct.product_id, PublishedProduct.slug).join(
                Product, Product.id == PublishedProduct.product_id
            ).where(
                PublishedProduct.storefront_id == storefront.id,
                PublishedProduct.is_active == True,
                Product.company_id == storefront.company_id,
                Product.is_active == True,
                Product.internal_reference.like("DEMO-%"),
                Product.sku.like("DMY-%"),
            )
        )
        published_rows = published_result.all()
        published_ids = [row.id for row in published_rows]
        product_ids = [row.product_id for row in published_rows]

        print(
            f"Storefront='{storefront.name}' ({storefront.subdomain}) "
            f"dummy_publicados={len(published_ids)}"
        )
        if published_rows:
            preview = ", ".join(row.slug for row in published_rows[:10])
            print(f"Slugs demo detectados: {preview}")

        if dry_run or not published_ids:
            if dry_run:
                print("Dry run activo. No se realizaron borrados.")
            return

        await db.execute(
            delete(StoreCollectionProduct).where(
                StoreCollectionProduct.published_product_id.in_(published_ids)
            )
        )
        await db.execute(
            delete(PublishedProduct).where(
                PublishedProduct.id.in_(published_ids)
            )
        )
        await db.execute(
            delete(Product).where(
                Product.id.in_(product_ids)
            )
        )
        await db.commit()
        print(
            f"Limpieza completada. published_products_borrados={len(published_ids)} "
            f"products_borrados={len(product_ids)}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Borra productos demo del storefront.")
    parser.add_argument("--subdomain", required=True, help="Subdominio del storefront, por ejemplo varyago.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra cuantos productos demo detecta, sin borrar.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(cleanup_dummy_products(arguments.subdomain, arguments.dry_run))
