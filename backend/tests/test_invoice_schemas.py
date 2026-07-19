import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.invoice import InvoiceFromSourceCreate, InvoicePaymentCreate


class InvoiceSchemaTests(unittest.TestCase):
    def test_sale_invoice_requires_only_a_sale_source(self):
        payload = InvoiceFromSourceCreate(type="SALE", sale_id=uuid4())
        self.assertEqual(payload.type, "SALE")

        with self.assertRaises(ValidationError):
            InvoiceFromSourceCreate(type="SALE", purchase_id=uuid4())

    def test_purchase_invoice_requires_only_a_purchase_source(self):
        payload = InvoiceFromSourceCreate(type="PURCHASE", purchase_id=uuid4())
        self.assertEqual(payload.type, "PURCHASE")

        with self.assertRaises(ValidationError):
            InvoiceFromSourceCreate(type="PURCHASE", purchase_id=uuid4(), sale_id=uuid4())

    def test_invoice_payment_must_be_positive(self):
        with self.assertRaises(ValidationError):
            InvoicePaymentCreate(amount=0, method="CASH")


if __name__ == "__main__":
    unittest.main()
