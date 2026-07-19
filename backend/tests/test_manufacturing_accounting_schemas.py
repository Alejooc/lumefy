import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.accounting import JournalIn, JournalLineIn
from app.schemas.manufacturing import BomIn, BomLineIn, ManufacturingOrderIn


class ManufacturingAccountingSchemaTests(unittest.TestCase):
    def test_bom_rejects_non_positive_component_quantity(self):
        with self.assertRaises(ValidationError):
            BomLineIn(component_id=uuid4(), quantity=0)

    def test_manufacturing_order_requires_positive_quantity(self):
        with self.assertRaises(ValidationError):
            ManufacturingOrderIn(bom_id=uuid4(), branch_id=uuid4(), quantity=0)

    def test_journal_lines_reject_negative_amounts(self):
        with self.assertRaises(ValidationError):
            JournalLineIn(account_id=uuid4(), debit=-1)

    def test_journal_accepts_balanced_input_structure(self):
        journal = JournalIn(lines=[
            JournalLineIn(account_id=uuid4(), debit=100),
            JournalLineIn(account_id=uuid4(), credit=100),
        ])
        self.assertEqual(len(journal.lines), 2)


if __name__ == "__main__":
    unittest.main()
