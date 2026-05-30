import unittest

from pydantic import ValidationError

from app.schemas.account_ledger import PaymentRequest
from app.schemas.client import ActivityCreate, ClientCreate, ClientUpdate


class ClientValidationTests(unittest.TestCase):
    def test_client_create_accepts_valid_payload(self):
        payload = ClientCreate(
            name="  Comercial Acme SAS  ",
            tax_id="900.123.456-7",
            email="cliente@acme.com",
            phone="+57 300 123 4567",
            address="Calle 10 # 20-30",
            notes="Cliente prioritario para ventas B2B.",
            status="ACTIVE",
            credit_limit=1500000,
        )

        self.assertEqual(payload.name, "Comercial Acme SAS")
        self.assertEqual(payload.tax_id, "900.123.456-7")
        self.assertEqual(payload.status, "active")

    def test_client_rejects_invalid_tax_id_characters(self):
        with self.assertRaises(ValidationError):
            ClientCreate(name="Cliente Demo", tax_id="ABC#123")

    def test_client_rejects_invalid_phone(self):
        with self.assertRaises(ValidationError):
            ClientCreate(name="Cliente Demo", phone="300-ABC-9999")

    def test_client_rejects_negative_credit_limit(self):
        with self.assertRaises(ValidationError):
            ClientCreate(name="Cliente Demo", credit_limit=-1)

    def test_client_update_converts_blank_optional_fields_to_none(self):
        payload = ClientUpdate(
            name="Cliente Editado",
            tax_id="   ",
            phone="   ",
            address="   ",
            notes="   ",
        )

        self.assertIsNone(payload.tax_id)
        self.assertIsNone(payload.phone)
        self.assertIsNone(payload.address)
        self.assertIsNone(payload.notes)

    def test_activity_requires_meaningful_content(self):
        with self.assertRaises(ValidationError):
            ActivityCreate(type="NOTE", content="  ")

        valid = ActivityCreate(type="CALL", content="  Se confirmo visita comercial.  ")
        self.assertEqual(valid.content, "Se confirmo visita comercial.")

    def test_payment_request_validates_amount_description_and_reference(self):
        valid = PaymentRequest(amount=250000, description="  Abono inicial  ", reference_id="  RCPT-1001  ")
        self.assertEqual(valid.description, "Abono inicial")
        self.assertEqual(valid.reference_id, "RCPT-1001")

        with self.assertRaises(ValidationError):
            PaymentRequest(amount=0, description="Pago")

        with self.assertRaises(ValidationError):
            PaymentRequest(amount=1500, description="  ")


if __name__ == "__main__":
    unittest.main()
