import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from pydantic import ValidationError

from app.api.v1.endpoints.storefront import _published_unit_price
from app.schemas.storefront_promotion import PromotionIn
from app.services.storefront_promotions import apply_promotion, choose_best_promotion


class StorefrontPromotionTests(unittest.TestCase):
    def test_percentage_is_applied_and_rounded_to_currency(self):
        promotion = SimpleNamespace(discount_percent=15)
        self.assertEqual(apply_promotion(100, promotion), (85.0, 15.0))
        self.assertEqual(apply_promotion(19.99, promotion), (16.99, 3.0))

    def test_overlapping_promotions_use_priority_then_discount(self):
        first = SimpleNamespace(priority=10, discount_percent=15, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), id=uuid4())
        second = SimpleNamespace(priority=20, discount_percent=5, created_at=datetime(2026, 1, 2, tzinfo=timezone.utc), id=uuid4())
        self.assertIs(choose_best_promotion([first, second]), second)

        same_priority_low = SimpleNamespace(priority=20, discount_percent=5, created_at=datetime(2026, 1, 3, tzinfo=timezone.utc), id=uuid4())
        self.assertIs(choose_best_promotion([second, same_priority_low]), same_priority_low)

    def test_input_requires_one_matching_target(self):
        with self.assertRaises(ValidationError):
            PromotionIn(
                storefront_id=uuid4(),
                name="Promo",
                target_type="COLLECTION",
                discount_percent=20,
            )

    def test_promotion_is_applied_after_the_effective_price_list_price(self):
        published = SimpleNamespace(price_override=None)
        product = SimpleNamespace(price=100.0)
        pricing = SimpleNamespace(base_price=80.0, variant_prices={})
        promotion = SimpleNamespace(discount_percent=25)

        list_price = _published_unit_price(published, product, None, pricing)
        self.assertEqual(list_price, 80.0)
        self.assertEqual(apply_promotion(list_price, promotion), (60.0, 20.0))

        with self.assertRaises(ValidationError):
            PromotionIn(
                storefront_id=uuid4(),
                name="Promo",
                target_type="PRODUCT",
                collection_id=uuid4(),
                published_product_id=uuid4(),
                discount_percent=20,
            )


if __name__ == "__main__":
    unittest.main()
