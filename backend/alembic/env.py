import asyncio
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Fix for Windows Asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from alembic import context

# Import your models here so Alembic can see them
from app.models.base import BaseModel
from app.models.user import User
from app.models.company import Company
from app.models.branch import Branch
from app.models.role import Role
from app.models.product import Product
from app.models.category import Category
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.sale import Sale, SaleItem, Payment
from app.models.client import Client
from app.models.audit import AuditLog
from app.models.supplier import Supplier
from app.models.purchase import PurchaseOrder
from app.models.purchase_item import PurchaseOrderItem
from app.models.pricelist import PriceList
from app.models.pricelist_item import PriceListItem
from app.models.plan import Plan
from app.models.system_setting import SystemSetting
from app.models.brand import Brand
from app.models.unit_of_measure import UnitOfMeasure
from app.models.product_variant import ProductVariant
from app.models.product_image import ProductImage
from app.models.logistics import PackageType, SalePackage, SalePackageItem

from app.core.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Overwrite the sqlalchemy.url in the config from the env variables
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = BaseModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
