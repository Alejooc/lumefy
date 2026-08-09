"""encrypt payment gateway credentials at rest

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.credential_crypto import (
    decrypt_credential,
    decrypt_sensitive_mapping,
    encrypt_credential,
    encrypt_sensitive_mapping,
)


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


gateway_table = sa.table(
    "store_payment_gateways",
    sa.column("id", sa.UUID()),
    sa.column("secret_key_encrypted", sa.String()),
    sa.column("extra_config", sa.JSON()),
)


def _rewrite_credentials(*, encrypt: bool) -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            gateway_table.c.id,
            gateway_table.c.secret_key_encrypted,
            gateway_table.c.extra_config,
        )
    ).mappings()

    for row in rows:
        if encrypt:
            secret = encrypt_credential(row["secret_key_encrypted"])
            extra_config = encrypt_sensitive_mapping(row["extra_config"])
        else:
            secret = decrypt_credential(row["secret_key_encrypted"])
            extra_config = decrypt_sensitive_mapping(row["extra_config"])

        connection.execute(
            gateway_table.update()
            .where(gateway_table.c.id == row["id"])
            .values(secret_key_encrypted=secret, extra_config=extra_config)
        )


def upgrade() -> None:
    _rewrite_credentials(encrypt=True)


def downgrade() -> None:
    _rewrite_credentials(encrypt=False)

