"""Read-only inventory for the multi-company boundary migration.

Run from ``backend`` and redirect stdout to keep the report as an artifact:

    python scripts/audit_tenant_boundaries.py > tenant-boundary-audit.json

The script never updates or deletes data. A non-zero exit code means either
the database could not be reached or at least one inconsistency was found.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Final

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Allow the documented ``python scripts/...`` invocation from ``backend``.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


CHECKS: Final[tuple[tuple[str, str], ...]] = (
    (
        "product_variants.tenant_boundary",
        """
        SELECT count(*)
        FROM product_variants AS variant
        LEFT JOIN products AS product ON product.id = variant.product_id
        WHERE variant.company_id IS NULL
           OR product.company_id IS NULL
           OR variant.company_id <> product.company_id
        """,
    ),
    ("price_lists.company_id_null", "SELECT count(*) FROM price_lists WHERE company_id IS NULL"),
    (
        "price_lists.source_tenant_boundary",
        """
        SELECT count(*)
        FROM price_lists AS pricelist
        JOIN integration_sources AS source ON source.id = pricelist.source_id
        WHERE pricelist.source_id IS NOT NULL
          AND (source.company_id IS NULL OR pricelist.company_id <> source.company_id)
        """,
    ),
    ("pricelist_items.company_id_null", "SELECT count(*) FROM pricelist_items WHERE company_id IS NULL"),
    (
        "pricelist_items.tenant_boundary",
        """
        SELECT count(*)
        FROM pricelist_items AS item
        LEFT JOIN price_lists AS pricelist ON pricelist.id = item.pricelist_id
        LEFT JOIN products AS product ON product.id = item.product_id
        LEFT JOIN product_variants AS variant ON variant.id = item.variant_id
        WHERE pricelist.company_id IS NULL
           OR product.company_id IS NULL
           OR item.company_id <> pricelist.company_id
           OR item.company_id <> product.company_id
           OR (
               item.variant_id IS NOT NULL
               AND (
                   variant.company_id IS NULL
                   OR item.company_id <> variant.company_id
                   OR variant.product_id <> item.product_id
               )
           )
        """,
    ),
    ("storefronts.company_id_null", "SELECT count(*) FROM storefronts WHERE company_id IS NULL"),
    (
        "storefronts.price_list_tenant_boundary",
        """
        SELECT count(*)
        FROM storefronts AS storefront
        JOIN price_lists AS pricelist ON pricelist.id = storefront.price_list_id
        WHERE storefront.price_list_id IS NOT NULL
          AND storefront.company_id <> pricelist.company_id
        """,
    ),
    (
        "published_products.tenant_boundary",
        """
        SELECT count(*)
        FROM published_products AS published
        LEFT JOIN storefronts AS storefront ON storefront.id = published.storefront_id
        LEFT JOIN products AS product ON product.id = published.product_id
        WHERE published.company_id IS NULL
           OR storefront.company_id IS NULL
           OR product.company_id IS NULL
           OR published.company_id <> storefront.company_id
           OR published.company_id <> product.company_id
        """,
    ),
    (
        "store_collection_products.tenant_boundary",
        """
        SELECT count(*)
        FROM store_collection_products AS link
        LEFT JOIN store_collections AS collection ON collection.id = link.collection_id
        LEFT JOIN published_products AS published ON published.id = link.published_product_id
        WHERE link.company_id IS NULL
           OR collection.company_id IS NULL
           OR published.company_id IS NULL
           OR link.company_id <> collection.company_id
           OR link.company_id <> published.company_id
        """,
    ),
    ("integration_sources.company_id_null", "SELECT count(*) FROM integration_sources WHERE company_id IS NULL"),
    (
        "integration_children.tenant_boundary",
        """
        SELECT count(*)
        FROM (
            SELECT child.company_id, source.company_id AS source_company_id
            FROM integration_sync_runs AS child
            LEFT JOIN integration_sources AS source ON source.id = child.source_id
            UNION ALL
            SELECT child.company_id, source.company_id
            FROM integration_record_links AS child
            LEFT JOIN integration_sources AS source ON source.id = child.source_id
            UNION ALL
            SELECT child.company_id, source.company_id
            FROM integration_product_prices AS child
            LEFT JOIN integration_sources AS source ON source.id = child.source_id
            UNION ALL
            SELECT child.company_id, source.company_id
            FROM integration_webhook_events AS child
            LEFT JOIN integration_sources AS source ON source.id = child.source_id
            UNION ALL
            SELECT child.company_id, source.company_id
            FROM pricelist_source_rules AS child
            LEFT JOIN integration_sources AS source ON source.id = child.source_id
        ) AS children
        WHERE company_id IS NULL
           OR source_company_id IS NULL
           OR company_id <> source_company_id
        """,
    ),
    (
        "integration_record_links.local_tenant_boundary",
        """
        SELECT count(*)
        FROM integration_record_links AS link
        LEFT JOIN products AS product ON product.id = link.local_product_id
        LEFT JOIN product_variants AS variant ON variant.id = link.local_variant_id
        WHERE (link.local_product_id IS NOT NULL AND (
                   product.company_id IS NULL OR link.company_id <> product.company_id
               ))
           OR (link.local_variant_id IS NOT NULL AND (
                   variant.company_id IS NULL OR link.company_id <> variant.company_id
               ))
        """,
    ),
    (
        "integration_product_prices.local_tenant_boundary",
        """
        SELECT count(*)
        FROM integration_product_prices AS price
        LEFT JOIN products AS product ON product.id = price.product_id
        LEFT JOIN product_variants AS variant ON variant.id = price.variant_id
        WHERE product.company_id IS NULL
           OR price.company_id <> product.company_id
           OR (price.variant_id IS NOT NULL AND (
                   variant.company_id IS NULL OR price.company_id <> variant.company_id
               ))
        """,
    ),
)


async def audit() -> int:
    if not settings.DATABASE_URL:
        print("DATABASE_URL no está configurada", file=sys.stderr)
        return 2

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            results = []
            for label, query in CHECKS:
                count = int((await connection.execute(text(query))).scalar_one())
                results.append({"check": label, "violations": count})
    except Exception:
        print("No fue posible ejecutar el auditor; verifica la conectividad con la base.", file=sys.stderr)
        return 2
    finally:
        await engine.dispose()

    report = {
        "read_only": True,
        "clean": all(item["violations"] == 0 for item in results),
        "checks": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(audit()))
