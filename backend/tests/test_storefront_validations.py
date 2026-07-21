import unittest
import asyncio
import hashlib
import hmac
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.endpoints.storefront import (
    _confirm_paid_storefront_sale,
    _format_payu_confirmation_amount,
    _has_valid_basic_auth,
    _has_valid_mercadopago_webhook_signature,
    _has_valid_payu_confirmation_signature,
    _has_valid_wompi_event_signature,
    _resolve_public_checkout_adjustments,
    _validate_payment_gateway_provider,
)
from app.schemas.storefront import (
    PublicCheckoutCustomer,
    PublicCheckoutPreviewRequest,
    PublicPaymentIntentRequest,
    PublicProduct,
)
from app.models.sale import SaleStatus
from app.models.inventory_movement import MovementType


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
        storefront = SimpleNamespace(
            id=uuid4(),
            company_id=uuid4(),
            checkout_settings={},
        )
        payload = PublicCheckoutPreviewRequest(items=[])
        self.assertEqual(
            asyncio.run(_resolve_public_checkout_adjustments(None, storefront, payload, 0)),
            (0.0, 0.0),
        )

        with self.assertRaisesRegex(HTTPException, "configuradas de la tienda"):
            asyncio.run(
                _resolve_public_checkout_adjustments(
                    None,
                    storefront,
                    PublicCheckoutPreviewRequest(items=[], discount_amount=10),
                    0,
                )
            )

    def test_payment_intent_requires_a_server_created_order(self):
        with self.assertRaises(ValidationError):
            PublicPaymentIntentRequest(provider="wompi")

    def test_only_operational_payment_providers_can_be_enabled(self):
        self.assertEqual(_validate_payment_gateway_provider("WOMPI"), "wompi")
        self.assertEqual(_validate_payment_gateway_provider("MercadoPago"), "mercadopago")
        self.assertEqual(_validate_payment_gateway_provider("whatsapp"), "whatsapp")
        with self.assertRaisesRegex(HTTPException, "Unsupported payment provider"):
            _validate_payment_gateway_provider("paypal")

    def test_paid_checkout_confirmation_is_idempotent_after_fulfillment_begins(self):
        sale = SimpleNamespace(status=SaleStatus.PICKING)
        self.assertTrue(asyncio.run(_confirm_paid_storefront_sale(None, sale)))

    def test_paid_checkout_reserves_available_stock_and_records_an_audit_event(self):
        product_id = uuid4()
        inventory = SimpleNamespace(quantity=10.0, reserved_quantity=3.0, average_cost=42.0)
        created_movements = []

        class Result:
            def scalars(self):
                return self

            def first(self):
                return inventory

        class Database:
            async def execute(self, _statement):
                return Result()

            def add(self, entity):
                created_movements.append(entity)

        sale = SimpleNamespace(
            id=uuid4(),
            status=SaleStatus.DRAFT,
            branch_id=uuid4(),
            warehouse_id=uuid4(),
            user_id=uuid4(),
            company_id=uuid4(),
            items=[
                SimpleNamespace(
                    product_id=product_id,
                    quantity=2.0,
                    product=SimpleNamespace(track_inventory=True),
                )
            ],
        )

        self.assertTrue(asyncio.run(_confirm_paid_storefront_sale(Database(), sale)))
        self.assertEqual(sale.status, SaleStatus.CONFIRMED)
        self.assertEqual(inventory.reserved_quantity, 5.0)
        self.assertEqual(len(created_movements), 1)
        self.assertEqual(created_movements[0].type, MovementType.RESERVE)
        self.assertEqual(created_movements[0].quantity, 0.0)
        self.assertEqual(created_movements[0].new_stock, 10.0)

    def test_wompi_event_signature_uses_declared_dynamic_properties(self):
        event = {
            "data": {"transaction": {
                "id": "1234-1610641025-49201",
                "status": "APPROVED",
                "amount_in_cents": 4490000,
            }},
            "signature": {
                "properties": [
                    "transaction.id",
                    "transaction.status",
                    "transaction.amount_in_cents",
                ],
            },
            "timestamp": 1530291411,
        }
        secret = "prod_events_OcHnIzeBl5socpwByQ4hA52Em3USQ93Z"
        checksum = hashlib.sha256(
            "1234-1610641025-49201APPROVED44900001530291411".encode("utf-8") + secret.encode("utf-8")
        ).hexdigest()
        self.assertTrue(_has_valid_wompi_event_signature(event, secret, checksum))
        self.assertFalse(_has_valid_wompi_event_signature(event, secret, "not-valid"))

    def test_payu_confirmation_signature_uses_the_provider_amount_format(self):
        payload = {
            "merchant_id": "508029",
            "reference_sale": "LUMEFY-0f66c4eb-71c3-44ee-9fc5-2970880a3994",
            "value": "150.00",
            "currency": "COP",
            "state_pol": "4",
        }
        api_key = "payu-api-key"
        raw = "payu-api-key~508029~LUMEFY-0f66c4eb-71c3-44ee-9fc5-2970880a3994~150.0~COP~4"
        payload["sign"] = hashlib.md5(raw.encode("utf-8")).hexdigest()
        self.assertEqual(_format_payu_confirmation_amount("150.00"), "150.0")
        self.assertTrue(_has_valid_payu_confirmation_signature(payload, api_key))
        payload["sign"] = "invalid"
        self.assertFalse(_has_valid_payu_confirmation_signature(payload, api_key))

    def test_mercadopago_webhook_signature_uses_payment_request_and_timestamp(self):
        payload = {"data": {"id": "123456789"}}
        secret = "mercadopago-webhook-secret"
        request_id = "request-42"
        timestamp = "1700000000"
        manifest = f"id:123456789;request-id:{request_id};ts:{timestamp};"
        signature = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertTrue(
            _has_valid_mercadopago_webhook_signature(
                payload,
                f"ts={timestamp},v1={signature}",
                request_id,
                secret,
            )
        )
        self.assertFalse(
            _has_valid_mercadopago_webhook_signature(payload, f"ts={timestamp},v1=invalid", request_id, secret)
        )

    def test_addi_callback_requires_the_configured_basic_auth_credentials(self):
        import base64

        authorization = "Basic " + base64.b64encode(b"addi-callback:callback-password").decode("ascii")
        self.assertTrue(_has_valid_basic_auth(authorization, "addi-callback", "callback-password"))
        self.assertFalse(_has_valid_basic_auth(authorization, "addi-callback", "wrong-password"))


if __name__ == "__main__":
    unittest.main()
