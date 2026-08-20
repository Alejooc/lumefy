import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from starlette.requests import Request

from app.api.v1.endpoints.storefront import subscribe_public_storefront_newsletter
from app.schemas.storefront import PublicNewsletterSubscriptionRequest


class StorefrontNewsletterTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_subscription_is_normalized_and_saved(self):
        storefront_id = uuid4()
        company_id = uuid4()
        storefront = SimpleNamespace(id=storefront_id, company_id=company_id)
        db = SimpleNamespace(
            scalar=AsyncMock(return_value=None),
            add=lambda value: setattr(db, "added", value),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )
        request = Request({"type": "http", "method": "POST", "path": "/newsletter", "headers": []})

        with patch(
            "app.api.v1.endpoints.storefront._get_public_storefront_by_id",
            new=AsyncMock(return_value=storefront),
        ):
            response = await subscribe_public_storefront_newsletter.__wrapped__(
                request=request,
                storefront_id=storefront_id,
                payload=PublicNewsletterSubscriptionRequest(email="Cliente@Example.com"),
                db=db,
            )

        self.assertEqual(db.added.email, "cliente@example.com")
        self.assertEqual(db.added.storefront_id, storefront_id)
        self.assertEqual(db.added.company_id, company_id)
        db.commit.assert_awaited_once()
        self.assertIn("registramos", response.msg)

    async def test_existing_active_subscription_is_idempotent(self):
        storefront_id = uuid4()
        existing = SimpleNamespace(is_active=True)
        storefront = SimpleNamespace(id=storefront_id, company_id=uuid4())
        db = SimpleNamespace(
            scalar=AsyncMock(return_value=existing),
            add=Mock(),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )
        request = Request({"type": "http", "method": "POST", "path": "/newsletter", "headers": []})

        with patch(
            "app.api.v1.endpoints.storefront._get_public_storefront_by_id",
            new=AsyncMock(return_value=storefront),
        ):
            response = await subscribe_public_storefront_newsletter.__wrapped__(
                request=request,
                storefront_id=storefront_id,
                payload=PublicNewsletterSubscriptionRequest(email="cliente@example.com"),
                db=db,
            )

        db.add.assert_not_called()
        db.commit.assert_not_awaited()
        self.assertIn("Ya estabas", response.msg)


if __name__ == "__main__":
    unittest.main()
