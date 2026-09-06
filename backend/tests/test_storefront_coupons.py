import unittest
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.api.v1.endpoints.storefront_coupons import _validate_coupon_values


class StorefrontCouponValidationTests(unittest.TestCase):
    def test_percentage_cannot_exceed_one_hundred(self):
        with self.assertRaises(HTTPException):
            _validate_coupon_values(
                discount_type="PERCENT",
                value=100.01,
                starts_at=None,
                ends_at=None,
            )

    def test_end_date_cannot_precede_start_date(self):
        start = datetime.now(timezone.utc) + timedelta(days=2)
        end = start - timedelta(days=1)
        with self.assertRaises(HTTPException):
            _validate_coupon_values(
                discount_type="FIXED",
                value=10,
                starts_at=start,
                ends_at=end,
            )

    def test_fixed_coupon_accepts_valid_dates(self):
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=1)
        _validate_coupon_values(
            discount_type=" fixed ",
            value=10,
            starts_at=start,
            ends_at=end,
        )


if __name__ == "__main__":
    unittest.main()
