import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.api.v1.endpoints.storefront import _storefront_preview_url, _theme_template_or_422
from app.services.storefront_theme import (
    HOME_SECTION_REGISTRY,
    build_home_document,
    normalize_home_document,
)


class StorefrontThemeContractTests(unittest.TestCase):
    def test_home_document_preserves_legacy_content_and_has_registered_sections(self):
        legacy_home = {
            "hero_slides": [{"id": "hero-legacy", "title": "Colección nueva"}],
            "category_section": {"title": "Compra por categoría"},
        }

        document = build_home_document({"home": legacy_home})
        normalized = normalize_home_document(document)

        self.assertEqual(normalized["legacy_home"], legacy_home)
        self.assertEqual(
            [section["type"] for section in normalized["sections"]],
            [item["type"] for item in HOME_SECTION_REGISTRY],
        )

    def test_empty_sections_are_expanded_for_legacy_documents(self):
        normalized = normalize_home_document(
            {
                "schema_version": 1,
                "template": "home",
                "legacy_home": {"newsletter": {"enabled": False}},
                "sections": [],
            }
        )

        self.assertTrue(normalized["sections"])
        self.assertEqual(normalized["legacy_home"]["newsletter"]["enabled"], False)

    def test_unknown_or_duplicate_sections_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "no permitida"):
            normalize_home_document({"template": "home", "sections": [{"id": "x", "type": "custom_html"}]})

        with self.assertRaisesRegex(ValueError, "repetido"):
            normalize_home_document(
                {
                    "template": "home",
                    "sections": [
                        {"id": "hero", "type": "hero"},
                        {"id": "hero", "type": "hero"},
                    ],
                }
            )

    def test_blocks_must_be_objects_and_payload_cannot_contain_executable_content(self):
        with self.assertRaisesRegex(ValueError, "deben ser objetos"):
            normalize_home_document(
                {"template": "home", "sections": [{"id": "hero", "type": "hero", "blocks": ["not-an-object"]}]}
            )

        with self.assertRaisesRegex(ValueError, "no está permitida"):
            normalize_home_document({"template": "home", "settings": {"onClick": "alert(1)"}})

        with self.assertRaisesRegex(ValueError, "no permitido"):
            normalize_home_document({"template": "home", "legacy_home": {"hero_slides": [{"image": "javascript:alert(1)"}]}})

    def test_preview_url_is_built_from_platform_domain_and_storefront_subdomain(self):
        from app.api.v1.endpoints import storefront as storefront_endpoint

        previous_domain = storefront_endpoint.settings.PLATFORM_STOREFRONT_DOMAIN
        try:
            storefront_endpoint.settings.PLATFORM_STOREFRONT_DOMAIN = "lumefy.shop"
            storefront = SimpleNamespace(id=uuid4(), subdomain="demo")
            self.assertEqual(_storefront_preview_url(storefront), "https://demo.lumefy.shop/")
        finally:
            storefront_endpoint.settings.PLATFORM_STOREFRONT_DOMAIN = previous_domain

    def test_template_registry_only_exposes_home_for_now(self):
        self.assertEqual(_theme_template_or_422("HOME"), "home")
        with self.assertRaises(HTTPException):
            _theme_template_or_422("custom")


if __name__ == "__main__":
    unittest.main()
