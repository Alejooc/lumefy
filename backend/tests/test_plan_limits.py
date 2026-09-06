import unittest
from datetime import datetime, timedelta, timezone

from app.core.plan_limits import subscription_access_state


class SubscriptionPolicyTests(unittest.TestCase):
    def test_active_and_past_due_are_allowed_only_before_expiry(self):
        now = datetime(2026, 9, 5, tzinfo=timezone.utc)
        future = (now + timedelta(days=1)).isoformat()
        self.assertEqual(
            subscription_access_state(
                is_active=True,
                subscription_status="ACTIVE",
                valid_until=future,
                now=now,
            ),
            "ACTIVE",
        )
        self.assertEqual(
            subscription_access_state(
                is_active=True,
                subscription_status="PAST_DUE",
                valid_until=future,
                now=now,
            ),
            "PAST_DUE",
        )
        self.assertEqual(
            subscription_access_state(
                is_active=True,
                subscription_status="PAST_DUE",
                valid_until=(now - timedelta(seconds=1)).isoformat(),
                now=now,
            ),
            "EXPIRED",
        )

    def test_suspended_cancelled_unknown_and_disabled_are_blocked(self):
        now = datetime(2026, 9, 5, tzinfo=timezone.utc)
        for subscription_status in ("SUSPENDED", "CANCELED", "UNKNOWN"):
            with self.subTest(subscription_status=subscription_status):
                self.assertEqual(
                    subscription_access_state(
                        is_active=True,
                        subscription_status=subscription_status,
                        valid_until=None,
                        now=now,
                    ),
                    "SUSPENDED",
                )
        self.assertEqual(
            subscription_access_state(
                is_active=False,
                subscription_status="ACTIVE",
                valid_until=None,
                now=now,
            ),
            "DISABLED",
        )

    def test_malformed_expiry_fails_closed(self):
        self.assertEqual(
            subscription_access_state(
                is_active=True,
                subscription_status="ACTIVE",
                valid_until="not-a-date",
            ),
            "INVALID_EXPIRY",
        )

    def test_date_only_expiry_remains_valid_through_that_day(self):
        self.assertEqual(
            subscription_access_state(
                is_active=True,
                subscription_status="ACTIVE",
                valid_until="2026-09-05",
                now=datetime(2026, 9, 5, 12, tzinfo=timezone.utc),
            ),
            "ACTIVE",
        )


if __name__ == "__main__":
    unittest.main()
