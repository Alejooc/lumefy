import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.procurement import PurchaseRequestCreate, PurchaseRequestItemCreate, SupplierQuoteCreate


class ProcurementSchemaTests(unittest.TestCase):
    def test_request_requires_at_least_one_positive_line(self):
        request = PurchaseRequestCreate(
            branch_id=uuid4(),
            items=[PurchaseRequestItemCreate(product_id=uuid4(), quantity=2)],
        )
        self.assertEqual(len(request.items), 1)

        with self.assertRaises(ValidationError):
            PurchaseRequestCreate(branch_id=uuid4(), items=[])

    def test_quote_rejects_negative_cost(self):
        with self.assertRaises(ValidationError):
            SupplierQuoteCreate(
                supplier_id=uuid4(),
                items=[{"product_id": uuid4(), "quantity": 1, "unit_cost": -1}],
            )


if __name__ == "__main__":
    unittest.main()
