import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from pydantic import ValidationError

from app.api.v1.endpoints.storefront import _published_unit_price
from app.schemas.storefront_promotion import PromotionIn
from app.services.storefront_promotions import (
    _buy_get_discount,
    apply_buy_x_get_y_promotions,
    apply_promotion,
    choose_best_promotion,
    filter_customer_eligible_promotions,
    meets_minimum_requirement,
)


class StorefrontPromotionTests(unittest.TestCase):
    def test_percentage_is_applied_and_rounded_to_currency(self):
        promotion = SimpleNamespace(discount_percent=15)
        self.assertEqual(apply_promotion(100, promotion), (85.0, 15.0))
        self.assertEqual(apply_promotion(19.99, promotion), (16.99, 3.0))

    def test_fixed_discount_is_capped_at_the_unit_price(self):
        promotion = SimpleNamespace(discount_type="FIXED", discount_value=12.5)
        self.assertEqual(apply_promotion(100, promotion), (87.5, 12.5))
        self.assertEqual(apply_promotion(8, promotion), (0.0, 8.0))

    def test_minimum_requirements_support_amount_and_quantity(self):
        amount = SimpleNamespace(minimum_requirement="AMOUNT", minimum_amount=350000)
        quantity = SimpleNamespace(minimum_requirement="QUANTITY", minimum_quantity=3)
        self.assertTrue(meets_minimum_requirement(amount, subtotal=350000, quantity=1))
        self.assertFalse(meets_minimum_requirement(amount, subtotal=349999, quantity=10))
        self.assertTrue(meets_minimum_requirement(quantity, subtotal=1, quantity=3))
        self.assertFalse(meets_minimum_requirement(quantity, subtotal=999999, quantity=2))

    def test_code_and_shipping_promotions_are_normalized(self):
        promotion = PromotionIn(
            storefront_id=uuid4(),
            name="Código verano",
            method="CODE",
            code=" verano10 ",
            target_type="ORDER",
            discount_type="FIXED",
            discount_value=25000,
        )
        self.assertEqual(promotion.code, "VERANO10")
        self.assertIsNone(promotion.discount_percent)

        shipping = PromotionIn(
            storefront_id=uuid4(),
            name="Envío gratis",
            target_type="SHIPPING",
            discount_type="FREE_SHIPPING",
        )
        self.assertEqual(shipping.discount_value, 0)

        with self.assertRaises(ValidationError):
            PromotionIn(
                storefront_id=uuid4(),
                name="Código sin valor",
                method="CODE",
                target_type="ORDER",
                discount_type="PERCENT",
            )

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

    def test_buy_x_get_y_normalizes_reward_and_legacy_discount_fields(self):
        collection_id = uuid4()
        promotion = PromotionIn(
            storefront_id=uuid4(),
            name="Compra dos lleva una gratis",
            promotion_type="BUY_X_GET_Y",
            target_type="COLLECTION",
            collection_id=collection_id,
            buy_quantity=2,
            get_quantity=1,
            get_discount_type="PERCENT",
            get_discount_value=100,
        )
        self.assertEqual(promotion.reward_target_type, "COLLECTION")
        self.assertEqual(promotion.reward_collection_id, collection_id)
        self.assertEqual(promotion.discount_type, "PERCENT")
        self.assertEqual(promotion.discount_value, 100)
        self.assertEqual(promotion.discount_percent, 100)

    def test_buy_x_get_y_fixed_reward_is_capped_at_the_unit_price(self):
        promotion = SimpleNamespace(get_discount_type="FIXED", get_discount_value=25)
        self.assertEqual(_buy_get_discount(100, promotion), 25.0)
        self.assertEqual(_buy_get_discount(12, promotion), 12.0)


class StorefrontBuyGetTests(unittest.IsolatedAsyncioTestCase):
    async def test_buy_x_get_y_applies_reward_to_cheapest_units(self):
        first_id = uuid4()
        second_id = uuid4()

        class FakeResult:
            def all(self):
                return [(first_id,), (second_id,)]

        class FakeDb:
            async def execute(self, _query):
                return FakeResult()

        rows = [
            SimpleNamespace(
                published_product_id=first_id,
                quantity=2,
                unit_price=100.0,
                line_subtotal=200.0,
                promotion_discount_amount=0.0,
                promotion_name=None,
                promotion_discount_type=None,
                promotion_discount_value=None,
                promotion_discount_percent=None,
            ),
            SimpleNamespace(
                published_product_id=second_id,
                quantity=1,
                unit_price=50.0,
                line_subtotal=50.0,
                promotion_discount_amount=0.0,
                promotion_name=None,
                promotion_discount_type=None,
                promotion_discount_value=None,
                promotion_discount_percent=None,
            ),
        ]
        promotion = SimpleNamespace(
            method="AUTOMATIC",
            combines_with_product=False,
            priority=0,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            id=uuid4(),
            target_type="COLLECTION",
            collection_id=uuid4(),
            reward_target_type="COLLECTION",
            reward_collection_id=uuid4(),
            published_product_id=None,
            reward_published_product_id=None,
            buy_quantity=2,
            get_quantity=1,
            get_discount_type="PERCENT",
            get_discount_value=100,
            name="Compra 2 lleva 1",
        )
        await apply_buy_x_get_y_promotions(FakeDb(), rows, [promotion])

        self.assertEqual(rows[0].line_subtotal, 200.0)
        self.assertEqual(rows[1].line_subtotal, 0.0)
        self.assertEqual(rows[1].promotion_discount_amount, 50.0)

    async def test_customer_eligibility_filters_new_and_returning_customers(self):
        class FakeDb:
            async def scalar(self, _query):
                return uuid4()

        storefront_id = uuid4()
        all_customers = SimpleNamespace(storefront_id=storefront_id, customer_eligibility="ALL")
        new_customers = SimpleNamespace(storefront_id=storefront_id, customer_eligibility="NEW_CUSTOMERS")
        returning_customers = SimpleNamespace(storefront_id=storefront_id, customer_eligibility="RETURNING_CUSTOMERS")

        without_email = await filter_customer_eligible_promotions(
            FakeDb(), [all_customers, new_customers, returning_customers], None
        )
        self.assertEqual(without_email, [all_customers])

        with_order = await filter_customer_eligible_promotions(
            FakeDb(), [all_customers, new_customers, returning_customers], "buyer@example.com"
        )
        self.assertEqual(with_order, [all_customers, returning_customers])


if __name__ == "__main__":
    unittest.main()
