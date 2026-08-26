import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.v1.endpoints.clients import create_client_activity, get_client_activities, get_client_timeline
from app.api.v1.endpoints.integrations import proxy_asset
from app.api.v1.endpoints.pos import get_pos_products
from app.api.v1.endpoints.products import _validate_product_relations, update_variant
from app.api.v1.endpoints.storefront import _public_asset_is_referenced, _resolve_public_asset_path
from app.api.v1.endpoints.users import update_user
from app.core.tenant import get_company_owned
from app.models.client import Client


class _Result:
    def __init__(self, record=None, rows=None):
        self.record = record
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.record

    def scalars(self):
        return SimpleNamespace(all=lambda: self.rows, first=lambda: self.record)


def _user(company_id):
    return SimpleNamespace(id=uuid4(), company_id=company_id, full_name="Tenant User")


class TenantIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_company_owned_helper_rejects_foreign_record(self):
        db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))

        with self.assertRaises(HTTPException) as context:
            await get_company_owned(db, Client, uuid4(), uuid4(), "Client not found")

        self.assertEqual(context.exception.status_code, 404)
        statement = db.execute.await_args.args[0]
        self.assertIn("clients.company_id", str(statement))

    async def test_variant_update_rejects_product_from_another_company(self):
        db = SimpleNamespace(execute=AsyncMock(return_value=_Result()), commit=AsyncMock())

        with self.assertRaises(HTTPException) as context:
            await update_variant(
                db=db,
                product_id=str(uuid4()),
                variant_id=str(uuid4()),
                variant_in=SimpleNamespace(model_dump=lambda **_: {}),
                current_user=_user(uuid4()),
            )

        self.assertEqual(context.exception.status_code, 404)
        db.commit.assert_not_awaited()

    async def test_activity_list_rejects_foreign_client(self):
        db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))

        with self.assertRaises(HTTPException) as context:
            await get_client_activities(
                db=db,
                client_id=uuid4(),
                current_user=_user(uuid4()),
            )

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(db.execute.await_count, 1)

    async def test_activity_creation_rejects_foreign_client_before_write(self):
        db = SimpleNamespace(execute=AsyncMock(return_value=_Result()), add=Mock())

        with self.assertRaises(HTTPException) as context:
            await create_client_activity(
                db=db,
                client_id=uuid4(),
                activity_in=SimpleNamespace(model_dump=lambda: {"type": "NOTE", "content": "x"}),
                current_user=_user(uuid4()),
            )

        self.assertEqual(context.exception.status_code, 404)
        db.add.assert_not_called()

    async def test_timeline_scopes_activities_and_ledger_to_company(self):
        company_id = uuid4()
        client = SimpleNamespace(id=uuid4(), company_id=company_id)
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    _Result(record=client),
                    _Result(rows=[]),
                    _Result(rows=[]),
                ]
            )
        )

        result = await get_client_timeline(
            db=db,
            client_id=client.id,
            current_user=_user(company_id),
        )

        self.assertEqual(result, [])
        activity_query = db.execute.await_args_list[1].args[0]
        ledger_query = db.execute.await_args_list[2].args[0]
        self.assertIn("client_activities.company_id", str(activity_query))
        self.assertIn("account_ledger.company_id", str(ledger_query))

    async def test_product_relations_reject_foreign_category(self):
        db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))

        with self.assertRaises(HTTPException) as context:
            await _validate_product_relations(
                db,
                uuid4(),
                {"category_id": uuid4()},
            )

        self.assertEqual(context.exception.status_code, 404)

    async def test_pos_products_reject_foreign_branch(self):
        db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))

        with self.assertRaises(HTTPException) as context:
            await get_pos_products(
                branch_id=uuid4(),
                price_list_id=None,
                db=db,
                current_user=_user(uuid4()),
            )

        self.assertEqual(context.exception.status_code, 404)

    async def test_public_proxy_does_not_use_authenticated_source_credentials(self):
        source = SimpleNamespace(
            id=uuid4(),
            auth_type="bearer",
            credentials={"token": "secret"},
            configuration={"asset_base_url": "https://provider.example/media"},
            base_url="https://provider.example/media",
        )
        db = SimpleNamespace(execute=AsyncMock(return_value=_Result(rows=[source])))

        with patch("app.api.v1.endpoints.integrations.request_asset", new=AsyncMock()) as request_asset:
            with self.assertRaises(HTTPException) as context:
                await proxy_asset(
                    url="https://provider.example/media/product.jpg",
                    source_id=source.id,
                    db=db,
                )

        self.assertEqual(context.exception.status_code, 403)
        request_asset.assert_not_awaited()

    async def test_user_cannot_change_own_role(self):
        user_id = uuid4()
        db = SimpleNamespace(execute=AsyncMock(), rollback=AsyncMock())
        current_user = _user(uuid4())
        current_user.id = user_id

        with self.assertRaises(HTTPException) as context:
            await update_user(
                db=db,
                user_id=user_id,
                user_in=SimpleNamespace(
                    model_dump=lambda **_: {"role_id": uuid4()},
                ),
                current_user=current_user,
            )

        self.assertEqual(context.exception.status_code, 403)
        db.execute.assert_not_awaited()

    async def test_public_proxy_does_not_select_an_unrelated_source_by_id(self):
        source = SimpleNamespace(
            id=uuid4(),
            auth_type="none",
            credentials={},
            configuration={"asset_base_url": "https://provider.example/media"},
            base_url="https://provider.example/media",
        )
        db = SimpleNamespace(execute=AsyncMock(return_value=_Result(rows=[source])))

        with patch("app.api.v1.endpoints.integrations.request_asset", new=AsyncMock()) as request_asset:
            with self.assertRaises(HTTPException) as context:
                await proxy_asset(
                    url="https://provider.example/media/product.jpg",
                    source_id=uuid4(),
                    db=db,
                )

        self.assertEqual(context.exception.status_code, 404)
        request_asset.assert_not_awaited()

    def test_public_media_path_rejects_backend_routes_and_traversal(self):
        for path in ("api/v1/products", "static/../api/v1/products"):
            with self.assertRaises(HTTPException) as context:
                _resolve_public_asset_path(path)
            self.assertEqual(context.exception.status_code, 404)

    async def test_public_asset_reference_is_limited_to_requested_storefront(self):
        storefront = SimpleNamespace(
            id=uuid4(),
            company_id=uuid4(),
            theme_settings={},
            checkout_settings={},
            seo_settings={},
        )
        company = SimpleNamespace(logo_url="/static/company-a/logo.png")
        db = SimpleNamespace(
            scalar=AsyncMock(side_effect=[None, None, None]),
            execute=AsyncMock(return_value=_Result(record=company)),
        )

        self.assertTrue(
            await _public_asset_is_referenced(
                db,
                storefront,
                "/static/company-a/logo.png",
            )
        )
        self.assertFalse(
            await _public_asset_is_referenced(
                SimpleNamespace(
                    scalar=AsyncMock(side_effect=[None, None, None]),
                    execute=AsyncMock(
                        return_value=_Result(
                            record=SimpleNamespace(logo_url="/static/company-b/logo.png")
                        )
                    ),
                ),
                storefront,
                "/static/company-a/other.png",
            )
        )
        published_product_query = str(db.scalar.await_args_list[0].args[0])
        self.assertIn("published_products.storefront_id", published_product_query)
        self.assertIn("published_products.company_id", published_product_query)

    async def test_public_asset_reference_accepts_published_theme_document(self):
        storefront = SimpleNamespace(
            id=uuid4(),
            company_id=uuid4(),
            theme_settings={},
            checkout_settings={},
            seo_settings={},
        )
        theme_document = SimpleNamespace(
            published_document={"legacy_home": {"hero_slides": [{"image": "/static/uploads/hero.png"}]}},
            draft_document={},
        )
        db = SimpleNamespace(
            scalar=AsyncMock(side_effect=[None, None, theme_document]),
            execute=AsyncMock(return_value=_Result(record=SimpleNamespace(logo_url=None))),
        )

        self.assertTrue(
            await _public_asset_is_referenced(
                db,
                storefront,
                "/static/uploads/hero.png",
            )
        )


if __name__ == "__main__":
    unittest.main()
