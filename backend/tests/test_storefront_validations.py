import unittest
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.endpoints.storefront import (
    _resolve_public_checkout_adjustments,
    _validate_payment_gateway_provider,
)
from app.schemas.storefront import (
    PublicCheckoutCustomer,
    PublicCheckoutPreviewRequest,
    PublicPaymentIntentRequest,
    PublicProduct,
)


class StorefrontValidationTests(unittest.TestCase):
    def test_checkout_requires_a_valid_customer_email(self):
        valid = PublicCheckoutCustomer(full_name="Cliente de prueba", email="cliente@example.com")
        self.assertEqual(str(valid.email), "cliente@example.com")

        with self.assertRaises(ValidationError):
            PublicCheckoutCustomer(full_name="Cliente de prueba", email="correo-invalido")

    def test_public_product_exposes_inventory_availability(self):
        product = PublicProduct(
            id=uuid4(),
            product_id=uuid4(),
            slug="producto-prueba",
            title="Producto de prueba",
            price=25000,
            base_price=25000,
            in_stock=False,
            stock_quantity=0,
        )

        self.assertFalse(product.in_stock)
        self.assertEqual(product.stock_quantity, 0)

    def test_checkout_adjustments_are_not_trusted_from_the_browser(self):
        self.assertEqual(
            _resolve_public_checkout_adjustments(PublicCheckoutPreviewRequest(items=[])),
            (0.0, 0.0),
        )

        with self.assertRaisesRegex(HTTPException, "server-side rules"):
            _resolve_public_checkout_adjustments(
                PublicCheckoutPreviewRequest(items=[], discount_amount=10)
            )

    def test_payment_intent_requires_a_server_created_order(self):
        with self.assertRaises(ValidationError):
            PublicPaymentIntentRequest(provider="wompi")

    def test_only_operational_payment_providers_can_be_enabled(self):
        self.assertEqual(_validate_payment_gateway_provider("WOMPI"), "wompi")
        with self.assertRaisesRegex(HTTPException, "Unsupported payment provider"):
            _validate_payment_gateway_provider("paypal")


if __name__ == "__main__":
    unittest.main()
