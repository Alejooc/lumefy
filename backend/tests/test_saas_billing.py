import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from pydantic import ValidationError

from app.api.v1.endpoints.admin import _billing_state
from app.schemas.saas_billing import SaaSBillingRecordCreate


class SaaSBillingTests(unittest.TestCase):
    def test_billing_record_normalizes_plan_and_rejects_invalid_period(self):
        record = SaaSBillingRecordCreate(
            plan_code="pro",
            period_start="2026-09-01T00:00:00Z",
            period_end="2026-10-01T00:00:00Z",
            amount="49.00",
        )
        self.assertEqual(record.plan_code, "PRO")
        self.assertEqual(str(record.amount), "49.00")

        with self.assertRaises(ValidationError):
            SaaSBillingRecordCreate(
                plan_code="PRO",
                period_start="2026-10-01T00:00:00Z",
                period_end="2026-09-01T00:00:00Z",
                amount=49,
            )

    def test_billing_portfolio_classifies_pending_overdue_and_due_soon(self):
        now = datetime.now(timezone.utc)
        self.assertEqual(
            _billing_state(
                valid_until=(now + timedelta(days=30)).isoformat(),
                latest_record=SimpleNamespace(status="PAID"),
                now=now,
            ),
            "PAID",
        )
        self.assertEqual(
            _billing_state(
                valid_until=(now + timedelta(days=30)).isoformat(),
                latest_record=SimpleNamespace(status="PENDING"),
                now=now,
            ),
            "PENDING",
        )
        self.assertEqual(
            _billing_state(
                valid_until=(now - timedelta(seconds=1)).isoformat(),
                latest_record=None,
                now=now,
            ),
            "OVERDUE",
        )
        self.assertEqual(
            _billing_state(
                valid_until=(now + timedelta(days=3)).isoformat(),
                latest_record=None,
                now=now,
            ),
            "DUE_SOON",
        )


if __name__ == "__main__":
    unittest.main()
