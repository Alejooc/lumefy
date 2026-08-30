from types import SimpleNamespace
import unittest

from app.services.storefront_collections import rules_match_product


class StorefrontCollectionRuleTests(unittest.TestCase):
    def test_title_starts_with_is_case_and_accent_insensitive(self):
        rules = [SimpleNamespace(field="title", operator="starts_with", value="cortina", is_active=True)]

        self.assertTrue(rules_match_product(rules, "all", {"title": "CÓRTINA Blackout"}))

    def test_all_conditions_excludes_a_forbidden_title_word(self):
        rules = [
            SimpleNamespace(field="title", operator="starts_with", value="cortina", is_active=True),
            SimpleNamespace(field="title", operator="not_contains", value="infantil", is_active=True),
        ]

        self.assertTrue(rules_match_product(rules, "all", {"title": "Cortina Blackout"}))
        self.assertFalse(rules_match_product(rules, "all", {"title": "Cortina Infantil"}))


if __name__ == "__main__":
    unittest.main()
