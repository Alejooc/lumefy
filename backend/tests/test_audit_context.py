import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from app.core.audit import log_activity, set_impersonation_context


class AuditContextTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        set_impersonation_context(None)

    async def asyncTearDown(self):
        set_impersonation_context(None)

    async def test_impersonation_context_is_embedded_in_business_audit_events(self):
        context = {
            "operator_user_id": "operator-id",
            "target_user_id": "target-id",
            "target_company_id": "company-id",
            "session_id": "session-id",
            "started_at": "2026-09-05T10:00:00+00:00",
            "reason": "Soporte de facturación",
        }
        set_impersonation_context(context)
        db = SimpleNamespace(add=Mock())

        await log_activity(
            db,
            action="UPDATE",
            entity_type="Company",
            entity_id="company-id",
            user_id="target-id",
            company_id="company-id",
            details={"field": "subscription_status"},
        )

        audit_log = db.add.call_args.args[0]
        self.assertEqual(audit_log.user_id, "target-id")
        self.assertEqual(audit_log.details["field"], "subscription_status")
        self.assertEqual(audit_log.details["impersonation"], context)


if __name__ == "__main__":
    unittest.main()
