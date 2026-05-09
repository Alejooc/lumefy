import argparse
import asyncio
import random
import re
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.product import Product
from app.models.storefront import PublishedProduct, StoreCollection, StoreCollectionProduct, Storefront


PRODUCT_NAMES = [
    "Sabana Premium",
    "Juego de Almohadas Confort",
    "Cobija Ligera",
    "Toalla Hotelera",
    "Cortina Blackout",
    "Cubrelecho Clasico",
    "Set Infantil Estrellas",
    "Sabana Satin Luxe",
    "Almohada Ergonomica",
    "Cobija Termica",
    "Toalla Spa Soft",
    "Cortina Decorativa",
    "Cubrelecho Nido",
    "Set Juvenil Color Pop",
    "Sabana Fresh Cotton",
    "Almohada Memory Plus",
    "Cobija Polar Home",
    "Toalla Cotton Max",
    "Cortina Aura",
    "Cubrelecho Royal",
]


def slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "producto-demo"


def build_description(name: str, collection_name: str) -> str:
    return (
        f"{name} pensada para ecommerce demo. "
        f"Pertenece a la coleccion {collection_name} y sirve para validar "
        "grillas, sliders, busquedas y filtros del storefront."
    )


async def seed_dummy_products(subdomain: str, count: int, featured_every: int) -> None:
    async with SessionLocal() as db:
        storefront_result = await db.execute(
            select(Storefront).where(
                Storefront.subdomain == subdomain,
                Storefront.is_active == True,
                Storefront.is_enabled == True,
            )
        )
        storefront = storefront_result.scalars().first()
        if not storefront:
            raise RuntimeError(f"No se encontro un storefront activo para '{subdomain}'.")

        collections_result = await db.execute(
            select(StoreCollection).where(
                StoreCollection.storefront_id == storefront.id,
                StoreCollection.is_active == True,
                StoreCollection.is_visible == True,
            ).order_by(StoreCollection.sort_order.asc(), StoreCollection.created_at.asc())
        )
        collections = collections_result.scalars().all()
        if not collections:
            raise RuntimeError("El storefront no tiene colecciones visibles para enlazar productos.")

        existing_result = await db.execute(
            select(PublishedProduct.slug).where(
                PublishedProduct.storefront_id == storefront.id,
                PublishedProduct.is_active == True,
            )
        )
        existing_slugs = set(existing_result.scalars().all())

        created = 0
        for index in range(count):
            collection = collections[index % len(collections)]
            base_name = PRODUCT_NAMES[index % len(PRODUCT_NAMES)]
            name = f"{base_name} Demo {index + 1:02d}"
            base_slug = slugify(name)
            slug = base_slug
            suffix = 2
            while slug in existing_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            existing_slugs.add(slug)

            price = float(Decimal(random.randrange(45000, 280000)) / Decimal("1"))
            compare_at = float(Decimal(price) * Decimal("1.18"))

            product = Product(
                name=name,
                internal_reference=f"DEMO-{index + 1:04d}",
                sku=f"DMY-{index + 1:04d}",
                description=build_description(name, collection.name),
                product_type="STORABLE",
                price=price,
                cost=round(price * 0.58, 2),
                tax_rate=19.0,
                track_inventory=True,
                min_stock=1.0,
                sale_ok=True,
                purchase_ok=True,
                company_id=storefront.company_id,
            )
            db.add(product)
            await db.flush()

            published = PublishedProduct(
                storefront_id=storefront.id,
                product_id=product.id,
                custom_title=name,
                custom_description=product.description,
                slug=slug,
                price_override=price,
                compare_at_price=compare_at,
                is_published=True,
                is_featured=(featured_every > 0 and (index + 1) % featured_every == 0),
                show_stock=True,
                sort_order=index,
                company_id=storefront.company_id,
            )
            db.add(published)
            await db.flush()

            db.add(
                StoreCollectionProduct(
                    collection_id=collection.id,
                    published_product_id=published.id,
                    sort_order=index,
                    company_id=storefront.company_id,
                )
            )
            created += 1

        await db.commit()
        print(
            f"Seed completado. Storefront='{storefront.name}' ({storefront.subdomain}), "
            f"colecciones={len(collections)}, productos_creados={created}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crea productos demo y los publica en un storefront.")
    parser.add_argument("--subdomain", required=True, help="Subdominio del storefront, por ejemplo varyago.")
    parser.add_argument("--count", type=int, default=12, help="Cantidad de productos demo a crear.")
    parser.add_argument(
        "--featured-every",
        type=int,
        default=4,
        help="Marca como destacados cada N productos. Usa 0 para desactivar.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(seed_dummy_products(arguments.subdomain, arguments.count, arguments.featured_every))
