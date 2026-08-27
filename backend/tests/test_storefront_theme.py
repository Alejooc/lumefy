import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.api.v1.endpoints.storefront import _storefront_preview_url, _theme_template_or_422
from app.services.storefront_theme import (
    HOME_SECTION_REGISTRY,
    PRODUCT_SECTION_REGISTRY,
    build_home_document,
    build_product_document,
    normalize_home_document,
    normalize_product_document,
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
            [item["type"] for item in HOME_SECTION_REGISTRY if item["type"] != "custom_embed"],
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

    def test_custom_html_is_filtered_to_presentational_markup(self):
        normalized = normalize_home_document(
            {
                "template": "home",
                "sections": [
                    {
                        "id": "custom-content",
                        "type": "custom_embed",
                        "settings": {
                            "mode": "html",
                            "content": '<h2 style="color:red" onclick="alert(1)">Hola</h2><img src="javascript:alert(1)" onerror="alert(1)">',
                        },
                    }
                ],
            }
        )

        content = normalized["sections"][0]["settings"]["content"]
        self.assertIn("<h2>Hola</h2>", content)
        self.assertNotIn("style=", content)
        self.assertNotIn("onclick", content)
        self.assertNotIn("onerror", content)
        self.assertNotIn("javascript:", content)

    def test_custom_iframe_uses_safe_url_and_bounded_height(self):
        normalized = normalize_home_document(
            {
                "template": "home",
                "sections": [
                    {
                        "id": "custom-video",
                        "type": "custom_embed",
                        "settings": {
                            "mode": "iframe",
                            "iframe_url": "https://player.vimeo.com/video/123",
                            "iframe_height": 5000,
                        },
                    }
                ],
            }
        )

        settings = normalized["sections"][0]["settings"]
        self.assertEqual(settings["iframe_url"], "https://player.vimeo.com/video/123")
        self.assertEqual(settings["iframe_height"], 900)
        self.assertEqual(settings["iframe_title"], "Contenido integrado")

        with self.assertRaisesRegex(ValueError, "no permitido"):
            normalize_home_document(
                {
                    "template": "home",
                    "sections": [
                        {"id": "custom-video", "type": "custom_embed", "settings": {"mode": "iframe", "iframe_url": "javascript:alert(1)"}}
                    ],
                }
            )

    def test_custom_iframe_markup_is_rejected_in_html_mode(self):
        with self.assertRaisesRegex(ValueError, "no permitido"):
            normalize_home_document(
                {
                    "template": "home",
                    "sections": [
                        {
                            "id": "custom-content",
                            "type": "custom_embed",
                            "settings": {"mode": "html", "content": '<iframe src="https://example.com"></iframe>'},
                        }
                    ],
                }
            )

    def test_section_design_is_normalized_to_theme_tokens(self):
        normalized = normalize_home_document(
            {
                "template": "home",
                "sections": [
                    {
                        "id": "hero",
                        "type": "hero",
                        "settings": {
                            "design": {
                                "width": "wide",
                                "background": "custom",
                                "background_color": "#12AB34",
                                "text": "custom",
                                "text_color": "not-a-color",
                                "radius": "round",
                                "shadow": "lifted",
                                "hide_mobile": True,
                                "style": "body { display: none; }",
                            }
                        },
                    }
                ],
            }
        )

        design = normalized["sections"][0]["settings"]["design"]
        self.assertEqual(design["width"], "wide")
        self.assertEqual(design["background_color"], "#12AB34")
        self.assertEqual(design["text_color"], "#1C274C")
        self.assertEqual(design["radius"], 30)
        self.assertEqual(design["shadow"], "lifted")
        self.assertTrue(design["hide_mobile"])
        self.assertNotIn("style", design)

    def test_product_document_has_registered_sections_and_content_defaults(self):
        normalized = normalize_product_document(build_product_document())

        self.assertEqual(normalized["template"], "product")
        self.assertEqual(
            [section["type"] for section in normalized["sections"]],
            [item["type"] for item in PRODUCT_SECTION_REGISTRY],
        )
        self.assertEqual(
            normalized["settings"]["content"]["breadcrumb_title"],
            "Detalle del producto",
        )

    def test_product_document_rejects_home_only_sections_and_duplicate_ids(self):
        with self.assertRaisesRegex(ValueError, "no permitida"):
            normalize_product_document(
                {"template": "product", "sections": [{"id": "hero", "type": "hero"}]}
            )

        with self.assertRaisesRegex(ValueError, "repetido"):
            normalize_product_document(
                {
                    "template": "product",
                    "sections": [
                        {"id": "gallery", "type": "product_gallery"},
                        {"id": "gallery", "type": "product_information"},
                    ],
                }
            )

    def test_preview_url_is_built_from_platform_domain_and_storefront_subdomain(self):
        from app.api.v1.endpoints import storefront as storefront_endpoint

        previous_domain = storefront_endpoint.settings.PLATFORM_STOREFRONT_DOMAIN
        try:
            storefront_endpoint.settings.PLATFORM_STOREFRONT_DOMAIN = "lumefy.shop"
            storefront = SimpleNamespace(id=uuid4(), subdomain="demo")
            self.assertEqual(_storefront_preview_url(storefront), "https://demo.lumefy.shop/")
        finally:
            storefront_endpoint.settings.PLATFORM_STOREFRONT_DOMAIN = previous_domain

    def test_preview_url_uses_http_and_configured_port_for_localhost(self):
        from app.api.v1.endpoints import storefront as storefront_endpoint

        previous_domain = storefront_endpoint.settings.PLATFORM_STOREFRONT_DOMAIN
        try:
            storefront_endpoint.settings.PLATFORM_STOREFRONT_DOMAIN = "localhost:3001"
            storefront = SimpleNamespace(id=uuid4(), subdomain="demo")
            self.assertEqual(_storefront_preview_url(storefront), "http://demo.localhost:3001/")
        finally:
            storefront_endpoint.settings.PLATFORM_STOREFRONT_DOMAIN = previous_domain

    def test_template_registry_exposes_supported_templates(self):
        self.assertEqual(_theme_template_or_422("HOME"), "home")
        self.assertEqual(_theme_template_or_422("PRODUCT"), "product")
        with self.assertRaises(HTTPException):
            _theme_template_or_422("custom")


if __name__ == "__main__":
    unittest.main()
