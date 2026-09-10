"""add customer eligibility segments to storefront promotions.

Revision ID: je0f1a2b3c4d
Revises: id8c9d0e1f2a
"""

from typing import Sequence, Union

from alembic import op


revision: str = "je0f1a2b3c4d"
down_revision: Union[str, None] = "id8c9d0e1f2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_storefront_promotion_customer_eligibility",
        "storefront_promotions",
        "customer_eligibility IN ('ALL', 'NEW_CUSTOMERS', 'RETURNING_CUSTOMERS')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_storefront_promotion_customer_eligibility",
        "storefront_promotions",
        type_="check",
    )
