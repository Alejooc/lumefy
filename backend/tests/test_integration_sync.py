import unittest
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import parse_qs, urlsplit

from pydantic import ValidationError

from app.schemas.integration import IntegrationInventoryScheduleUpdate, IntegrationSyncRunOut
from app.services.integration_service import _fetch_entity, _fetch_inventory, _mapped, _sync_inventory


class IntegrationScheduleSchemaTests(unittest.TestCase):
    def test_automatic_schedule_requires_a_valid_interval(self):
        with self.assertRaises(ValidationError):
            IntegrationInventoryScheduleUpdate(mode="AUTOMATIC", interval_minutes=None)
        with self.assertRaises(ValidationError):
            IntegrationInventoryScheduleUpdate(mode="AUTOMATIC", interval_minutes=1)

        schedule = IntegrationInventoryScheduleUpdate(mode="AUTOMATIC", interval_minutes=15)

        self.assertEqual(schedule.interval_minutes, 15)

    def test_manual_schedule_discards_an_interval(self):
        schedule = IntegrationInventoryScheduleUpdate(mode="MANUAL", interval_minutes=30)

        self.assertIsNone(schedule.interval_minutes)


class IntegrationProviderShapeTests(unittest.TestCase):
    def test_catalog_accepts_provider_product_id_and_product_name_fields(self):
        item = {
            "product_id": "10536",
            "product_name": "JUEGO DE SABANAS UNICOLOR",
            "sku": "THO12306",
        }
        mapping = {"product.external_id": "id", "product.name": "name"}

        external_id = _mapped(item, mapping, "product.external_id", "id", "external_id", "uuid", "product_id")
        name = _mapped(item, mapping, "product.name", "name", "title", "product_name")

        self.assertEqual(external_id, "10536")
        self.assertEqual(name, "JUEGO DE SABANAS UNICOLOR")

    def test_queued_run_can_be_serialized_without_a_start_time(self):
        now = datetime.utcnow()
        run = IntegrationSyncRunOut(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            sync_type="INVENTORY",
            trigger_type="MANUAL",
            status="QUEUED",
            queued_at=now,
            started_at=None,
            finished_at=None,
            products_processed=0,
            products_created=0,
            products_updated=0,
            inventory_processed=0,
            inventory_updated=0,
            items_failed=0,
            details={},
            error_message=None,
            created_at=now,
        )

        self.assertEqual(run.status, "QUEUED")
        self.assertIsNone(run.started_at)


class IntegrationInventoryIdempotencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_repeated_payload_identity_creates_one_inventory_row(self):
        company_id = uuid.uuid4()
        product = SimpleNamespace(id=uuid.uuid4(), company_id=company_id)
        branch = SimpleNamespace(id=uuid.uuid4())
        warehouse = SimpleNamespace(id=uuid.uuid4())
        source = SimpleNamespace(id=uuid.uuid4(), company_id=company_id, configuration={})
        run = SimpleNamespace(inventory_processed=0, inventory_updated=0, items_failed=0, details={})
        query_result = Mock()
        query_result.scalars.return_value.first.return_value = None
        db = SimpleNamespace(
            execute=AsyncMock(return_value=query_result),
            add=Mock(),
            flush=AsyncMock(),
        )

        with (
            patch("app.services.integration_service._fetch_entity", new=AsyncMock(return_value=[])),
            patch(
                "app.services.integration_service._resolve_inventory_location",
                new=AsyncMock(return_value=(branch, warehouse)),
            ),
        ):
            await _sync_inventory(
                db,
                source,
                run,
                embedded_inventory=[
                    {"product": product, "variant": None, "quantity": 7},
                    {"product": product, "variant": None, "quantity": -9},
                ],
            )

        self.assertEqual(db.add.call_count, 1)
        db.flush.assert_awaited_once()
        created_inventory = db.add.call_args.args[0]
        self.assertEqual(created_inventory.quantity, 0)
        self.assertEqual(run.inventory_processed, 2)
        self.assertEqual(run.inventory_updated, 2)


class IntegrationInventoryBatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_inventory_uses_provider_limit_and_data_rows(self):
        source = SimpleNamespace(
            id=uuid.uuid4(),
            base_url="https://provider.example.com",
            auth_type="none",
            credentials={},
            configuration={
                "endpoints": {
                    "inventory": {
                        "path": "/api/external/inventory",
                        "data_path": "data",
                        "batch": {"enabled": True, "query_param": "skus", "size": 100},
                    }
                }
            },
        )
        sku_map = {f"sku:SKU{index:03d}": object() for index in range(101)}
        requests = []

        async def request_json(url, headers):
            requests.append(url)
            requested_skus = parse_qs(urlsplit(url).query)["skus"][0].split(",")
            return 200, {
                "tipo": 1,
                "msg": "OK",
                "data": [{"sku": sku, "stock": "0", "product_id": sku} for sku in requested_skus],
                "meta": {"count": len(requested_skus)},
            }

        progress = []

        async def on_progress(value):
            progress.append(value)

        with patch("app.services.integration_service._request_json", new=request_json):
            rows = await _fetch_inventory(SimpleNamespace(), source, sku_map, {}, on_progress)

        self.assertEqual(len(requests), 2)
        self.assertEqual(len(parse_qs(urlsplit(requests[0]).query)["skus"][0].split(",")), 100)
        self.assertEqual(len(parse_qs(urlsplit(requests[1]).query)["skus"][0].split(",")), 1)
        self.assertEqual(len(rows), 101)
        self.assertEqual(rows[0]["stock"], "0")
        self.assertEqual(progress[-1]["percent"], 40)


class IntegrationProgressTests(unittest.IsolatedAsyncioTestCase):
    async def test_pagination_reports_progress_and_honors_response_page_count(self):
        source = SimpleNamespace(
            base_url="https://provider.example.com/api",
            auth_type="none",
            credentials={},
            configuration={
                "endpoints": {
                    "products": {
                        "path": "/products",
                        "pagination": {
                            "enabled": True,
                            "type": "page",
                            "page_param": "page",
                            "per_page_param": "per_page",
                            "per_page": 2,
                            "max_pages": 50,
                        },
                    }
                }
            },
        )
        requests = []

        async def request_json(url, headers):
            requests.append(url)
            page = len(requests)
            return 200, {
                "data": [{"id": f"{page}-a"}, {"id": f"{page}-b"}],
                "meta": {"page": page, "pages": 2, "total": 4},
            }

        progress = []

        async def on_progress(value):
            progress.append(value)

        with patch("app.services.integration_service._request_json", new=request_json):
            rows = await _fetch_entity(source, "products", on_progress)

        self.assertEqual(len(rows), 4)
        self.assertEqual(len(requests), 2)
        self.assertEqual(progress[-1]["items_received"], 4)
        self.assertEqual(progress[-1]["pages_total"], 2)
        self.assertEqual(progress[-1]["percent"], 40)


if __name__ == "__main__":
    unittest.main()
