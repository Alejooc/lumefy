from types import SimpleNamespace
from unittest import TestCase
from uuid import uuid4

from app.api.v1.endpoints.products import (
    _PRODUCT_EXPORT_COLUMNS,
    _build_product_export_rows,
    _complete_relative_image_url,
    _normalize_import_dataframe,
)


class ProductExportTests(TestCase):
    def _product(self, variants=None):
        return SimpleNamespace(
            id=uuid4(),
            name="Juego de sábanas",
            sku=None,
            barcode=None,
            product_type="STORABLE",
            price=37000,
            cost=12000,
            tax_rate=19,
            min_stock=0,
            track_inventory=True,
            sale_ok=True,
            purchase_ok=True,
            is_active=True,
            image_url="imagenes/sabanas.jpg",
            category=SimpleNamespace(name="Hogar"),
            brand=SimpleNamespace(name="Lumefy"),
            variants=variants or [],
        )

    def test_variant_sku_and_ids_are_exported(self):
        product = self._product(
            [
                SimpleNamespace(
                    id=uuid4(),
                    name="Doble - 1.40 x 1.90",
                    sku="THO12306",
                    barcode=None,
                    price_extra=0,
                    cost_extra=0,
                    price=37000,
                    cost=12000,
                    attributes={"size": "Doble"},
                    weight=None,
                    is_active=True,
                )
            ]
        )

        rows = _build_product_export_rows([product])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_id"], str(product.id))
        self.assertEqual(rows[0]["variant_id"], str(product.variants[0].id))
        self.assertEqual(rows[0]["sku"], "")
        self.assertEqual(rows[0]["variant_sku"], "THO12306")
        self.assertEqual(set(_PRODUCT_EXPORT_COLUMNS), set(rows[0]))

    def test_products_without_variants_keep_a_single_product_row(self):
        product = self._product()

        rows = _build_product_export_rows([product])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_id"], str(product.id))
        self.assertEqual(rows[0]["variant_id"], "")

    def test_old_spanish_headers_are_accepted_by_import_normalizer(self):
        import pandas as pd

        dataframe = _normalize_import_dataframe(
            pd.DataFrame(columns=["ID producto", "ID variante", "Nombre", "SKU variante"])
        )

        self.assertEqual(
            list(dataframe.columns), ["product_id", "variant_id", "name", "variant_sku"]
        )

    def test_image_url_completion_keeps_existing_absolute_urls_by_default(self):
        value, changed = _complete_relative_image_url(
            "https://old.example.test/static/catalog/THO12306.jpg",
            "https://cdn.example.test/images/",
        )

        self.assertEqual(value, "https://old.example.test/static/catalog/THO12306.jpg")
        self.assertFalse(changed)

    def test_image_url_completion_can_replace_an_incorrect_absolute_base(self):
        value, changed = _complete_relative_image_url(
            "https://old.example.test/static/catalog/THO12306.jpg",
            "https://cdn.example.test/images/",
            replace_existing=True,
        )

        self.assertEqual(value, "https://cdn.example.test/images/static/catalog/THO12306.jpg")
        self.assertTrue(changed)

    def test_image_url_completion_preserves_nested_relative_path(self):
        value, changed = _complete_relative_image_url(
            "products/12529/9_b4.jpg",
            "https://cdn.example.test/",
        )

        self.assertEqual(value, "https://cdn.example.test/products/12529/9_b4.jpg")
        self.assertTrue(changed)
