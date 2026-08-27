import unittest

from app.services.storefront_checkout import normalize_checkout_settings


class StorefrontCheckoutAppearanceTests(unittest.TestCase):
    def test_appearance_uses_global_theme_defaults(self):
        settings = normalize_checkout_settings(
            {"allow_guest_checkout": True},
            {
                "global": {
                    "styles": {
                        "primary_color": "#123456",
                        "page_background_color": "#f0f1f2",
                    }
                }
            },
        )

        self.assertEqual(settings["allow_guest_checkout"], True)
        self.assertEqual(settings["appearance"]["accent_color"], "#123456")
        self.assertEqual(settings["appearance"]["background_color"], "#f0f1f2")

    def test_appearance_rejects_unsafe_values_and_clamps_radius(self):
        settings = normalize_checkout_settings(
            {
                "appearance": {
                    "background_color": "url(javascript:alert(1))",
                    "accent_color": "#123456; color:red",
                    "radius": 999,
                    "layout": "freeform",
                    "show_logo": False,
                }
            }
        )

        appearance = settings["appearance"]
        self.assertEqual(appearance["background_color"], "#f4f6fb")
        self.assertEqual(appearance["accent_color"], "#3c50e0")
        self.assertEqual(appearance["radius"], 24)
        self.assertEqual(appearance["layout"], "split")
        self.assertFalse(appearance["show_logo"])

    def test_appearance_is_backwards_compatible_with_empty_settings(self):
        settings = normalize_checkout_settings(None)

        self.assertEqual(settings["appearance"]["layout"], "split")
        self.assertTrue(settings["appearance"]["show_brand_name"])


if __name__ == "__main__":
    unittest.main()
