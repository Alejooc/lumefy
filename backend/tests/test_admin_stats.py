import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.api.v1.endpoints.admin import read_admin_stats


class AdminStatsTests(unittest.IsolatedAsyncioTestCase):
    async def test_stats_use_real_plan_prices_and_current_subscription_state(self):
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        companies = [
            SimpleNamespace(plan="PRO", subscription_status="ACTIVE", valid_until=future, is_active=True),
            SimpleNamespace(plan="PRO", subscription_status="PAST_DUE", valid_until=future, is_active=True),
            SimpleNamespace(plan="FREE", subscription_status="ACTIVE", valid_until=future, is_active=True),
            SimpleNamespace(plan="ENTERPRISE", subscription_status="SUSPENDED", valid_until=future, is_active=True),
            SimpleNamespace(plan="PRO", subscription_status="ACTIVE", valid_until=expired, is_active=True),
            SimpleNamespace(plan="LEGACY", subscription_status="ACTIVE", valid_until=future, is_active=True),
        ]
        plans = [
            SimpleNamespace(code="PRO", price=49, currency="USD", duration_days=30),
            SimpleNamespace(code="FREE", price=0, currency="USD", duration_days=30),
            SimpleNamespace(code="ENTERPRISE", price=199, currency="USD", duration_days=365),
        ]
        company_result = Mock()
        company_result.all.return_value = companies
        users_result = Mock()
        users_result.scalar.return_value = 7
        plans_result = Mock()
        plans_result.scalars.return_value.all.return_value = plans
        db = SimpleNamespace(
            execute=AsyncMock(side_effect=[company_result, users_result, plans_result])
        )

        result = await read_admin_stats(db=db, current_user=SimpleNamespace(is_superuser=True))

        self.assertEqual(result["total_companies"], 6)
        self.assertEqual(result["active_companies"], 6)
        self.assertEqual(result["total_users"], 7)
        self.assertEqual(result["active_subscriptions"], {"PRO": 2, "FREE": 1, "LEGACY": 1})
        self.assertEqual(result["paid_subscription_count"], 2)
        self.assertEqual(result["mrr"], 98.0)
        self.assertEqual(result["mrr_currency"], "USD")
        self.assertTrue(result["mrr_is_estimate"])
        self.assertEqual(result["subscription_statuses"]["SUSPENDED"], 1)
        self.assertEqual(result["unpriced_active_subscriptions"], 1)


if __name__ == "__main__":
    unittest.main()
