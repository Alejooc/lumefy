import unittest
from datetime import timedelta

import jwt

from app.core.auth import create_access_token
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


if __name__ == "__main__":
    unittest.main()

