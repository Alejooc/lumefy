import unittest
from datetime import timedelta
from uuid import uuid4

import jwt

from app.core.auth import create_access_token, get_storefront_preview_claims
from app.core.config import settings


class AuthTokenTests(unittest.TestCase):
    def test_access_token_round_trip_preserves_supported_claims(self):
        token = create_access_token(
            {"sub": "customer@example.com", "scope": "storefront"},
            expires_delta=timedelta(minutes=5),
        )

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        self.assertEqual(payload["sub"], "customer@example.com")
        self.assertEqual(payload["scope"], "storefront")
        self.assertIn("exp", payload)

    def test_expired_token_is_rejected(self):
        token = create_access_token(
            {"sub": "customer@example.com"},
            expires_delta=timedelta(seconds=-1),
        )

        with self.assertRaises(jwt.ExpiredSignatureError):
            jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    def test_preview_token_is_scoped_to_storefront_and_template(self):
        storefront_id = uuid4()
        company_id = uuid4()
        token = create_access_token(
            {
                "sub": str(uuid4()),
                "scope": "storefront_theme_preview",
                "storefront_id": str(storefront_id),
                "company_id": str(company_id),
                "template_key": "home",
            },
            expires_delta=timedelta(minutes=5),
        )

        self.assertEqual(
            get_storefront_preview_claims(token),
            (storefront_id, company_id, "home"),
        )

        product_token = create_access_token(
            {
                "scope": "storefront_theme_preview",
                "storefront_id": str(storefront_id),
                "company_id": str(company_id),
                "template_key": "product",
            },
            expires_delta=timedelta(minutes=5),
        )
        self.assertEqual(
            get_storefront_preview_claims(product_token),
            (storefront_id, company_id, "product"),
        )

        wrong_scope = create_access_token(
            {"scope": "storefront", "storefront_id": str(storefront_id), "company_id": str(company_id), "template_key": "home"},
            expires_delta=timedelta(minutes=5),
        )
        self.assertIsNone(get_storefront_preview_claims(wrong_scope))

        expired = create_access_token(
            {
                "scope": "storefront_theme_preview",
                "storefront_id": str(storefront_id),
                "company_id": str(company_id),
                "template_key": "home",
            },
            expires_delta=timedelta(seconds=-1),
        )
        self.assertIsNone(get_storefront_preview_claims(expired))

        unsupported_template = create_access_token(
            {
                "scope": "storefront_theme_preview",
                "storefront_id": str(storefront_id),
                "company_id": str(company_id),
                "template_key": "checkout",
            },
            expires_delta=timedelta(minutes=5),
        )
        self.assertIsNone(get_storefront_preview_claims(unsupported_template))


if __name__ == "__main__":
    unittest.main()

