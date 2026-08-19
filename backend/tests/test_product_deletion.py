import unittest
import os
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.api.v1.endpoints.products import _PRODUCT_DELETE_RELATIONS, _find_product_delete_blockers
from app.schemas.product import ProductBulkDeleteRequest
from app.services.integration_service import (
    prune_orphaned_local_assets,
    remove_unreferenced_local_assets,
)


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    class _Scalars:
        def __init__(self, values):
            self._values = values

        def all(self):
            return self._values

    def scalars(self):
        return self._Scalars(self._values)


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


class LocalIntegrationAssetCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_unreferenced_provider_asset_is_removed_from_disk(self):
        source_id = uuid.uuid4()
        filename = f"{'a' * 64}.jpg"
        asset_url = f"/static/uploads/integrations/{source_id}/{filename}"
        with tempfile.TemporaryDirectory() as directory:
            asset_path = Path(directory) / str(source_id) / filename
            asset_path.parent.mkdir(parents=True)
            asset_path.write_bytes(b"image")
            previous_directory = os.environ.get("INTEGRATION_ASSET_DIR")
            os.environ["INTEGRATION_ASSET_DIR"] = directory
            try:
                db = SimpleNamespace(
                    execute=AsyncMock(
                        side_effect=[_ScalarResult([]), _ScalarResult([])]
                    )
                )
                removed = await remove_unreferenced_local_assets(db, {asset_url})
                exists_after_cleanup = asset_path.exists()
            finally:
                if previous_directory is None:
                    os.environ.pop("INTEGRATION_ASSET_DIR", None)
                else:
                    os.environ["INTEGRATION_ASSET_DIR"] = previous_directory

        self.assertEqual(removed, 1)
        self.assertFalse(exists_after_cleanup)

    async def test_shared_provider_asset_is_kept_when_still_referenced(self):
        source_id = uuid.uuid4()
        filename = f"{'b' * 64}.png"
        asset_url = f"/static/uploads/integrations/{source_id}/{filename}"
        with tempfile.TemporaryDirectory() as directory:
            asset_path = Path(directory) / str(source_id) / filename
            asset_path.parent.mkdir(parents=True)
            asset_path.write_bytes(b"image")
            previous_directory = os.environ.get("INTEGRATION_ASSET_DIR")
            os.environ["INTEGRATION_ASSET_DIR"] = directory
            try:
                db = SimpleNamespace(
                    execute=AsyncMock(
                        side_effect=[_ScalarResult([asset_url]), _ScalarResult([])]
                    )
                )
                removed = await remove_unreferenced_local_assets(db, {asset_url})
                exists_after_shared = asset_path.exists()
            finally:
                if previous_directory is None:
                    os.environ.pop("INTEGRATION_ASSET_DIR", None)
                else:
                    os.environ["INTEGRATION_ASSET_DIR"] = previous_directory

        self.assertEqual(removed, 0)
        self.assertTrue(exists_after_shared)

    async def test_orphaned_provider_assets_are_pruned(self):
        source_id = uuid.uuid4()
        filename = f"{'c' * 64}.webp"
        with tempfile.TemporaryDirectory() as directory:
            asset_path = Path(directory) / str(source_id) / filename
            asset_path.parent.mkdir(parents=True)
            asset_path.write_bytes(b"image")
            previous_directory = os.environ.get("INTEGRATION_ASSET_DIR")
            os.environ["INTEGRATION_ASSET_DIR"] = directory
            try:
                db = SimpleNamespace(
                    execute=AsyncMock(
                        side_effect=[_ScalarResult([]), _ScalarResult([])]
                    )
                )
                removed = await prune_orphaned_local_assets(db)
                exists_after_cleanup = asset_path.exists()
            finally:
                if previous_directory is None:
                    os.environ.pop("INTEGRATION_ASSET_DIR", None)
                else:
                    os.environ["INTEGRATION_ASSET_DIR"] = previous_directory

        self.assertEqual(removed, 1)
        self.assertFalse(exists_after_cleanup)


if __name__ == "__main__":
    unittest.main()
