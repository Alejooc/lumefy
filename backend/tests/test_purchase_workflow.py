import unittest

from fastapi import HTTPException

from app.api.v1.endpoints.purchases import _validate_purchase_status_transition
from app.models.purchase import PurchaseStatus


class PurchaseWorkflowTests(unittest.TestCase):
    def test_purchase_administrative_transitions_are_limited(self):
        _validate_purchase_status_transition(PurchaseStatus.DRAFT, PurchaseStatus.VALIDATION)
        _validate_purchase_status_transition(PurchaseStatus.VALIDATION, PurchaseStatus.CONFIRMED)

        with self.assertRaisesRegex(HTTPException, "Recibir productos"):
            _validate_purchase_status_transition(PurchaseStatus.CONFIRMED, PurchaseStatus.RECEIVED)

        with self.assertRaisesRegex(HTTPException, "No se puede cambiar"):
            _validate_purchase_status_transition(PurchaseStatus.PARTIAL, PurchaseStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()
