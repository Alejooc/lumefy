import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.api.v1.endpoints.products import _PRODUCT_DELETE_RELATIONS, _find_product_delete_blockers
from app.schemas.product import ProductBulkDeleteRequest


class ProductDeleteGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_sale_relation_is_reported_as_a_blocker(self):
        product_id = uuid.uuid4()
        query_results = []
        for index, _ in enumerate(_PRODUCT_DELETE_RELATIONS):
            result = Mock()
            result.scalars.return_value.all.return_value = [product_id] if index == 0 else []
            query_results.append(result)

        db = SimpleNamespace(execute=AsyncMock(side_effect=query_results))

        blockers = await _find_product_delete_blockers(db, [product_id])

        self.assertEqual(blockers[product_id], ["Tiene una orden o venta asociada"])
        self.assertEqual(db.execute.await_count, len(_PRODUCT_DELETE_RELATIONS))


class ProductBulkDeleteSchemaTests(unittest.TestCase):
    def test_request_requires_at_least_one_product(self):
        with self.assertRaises(ValueError):
            ProductBulkDeleteRequest(product_ids=[])

    def test_request_accepts_a_bounded_selection(self):
        product_ids = [uuid.uuid4(), uuid.uuid4()]
        request = ProductBulkDeleteRequest(product_ids=product_ids)

        self.assertEqual(request.product_ids, product_ids)

    def test_whole_catalog_request_can_explicitly_archive_history(self):
        from app.schemas.product import ProductBulkDeleteAllRequest

        request = ProductBulkDeleteAllRequest(force=True)

        self.assertTrue(request.force)


if __name__ == "__main__":
    unittest.main()
