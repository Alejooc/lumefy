"""Add encrypted platform MFA state and revocable JWT versions."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ga5f6a7b8c9d0"
down_revision: Union[str, None] = "fz4e5f6a7b8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("mfa_secret_encrypted", sa.String(), nullable=True))
    op.add_column("users", sa.Column("mfa_recovery_codes_encrypted", sa.String(), nullable=True))
    op.add_column("users", sa.Column("mfa_last_used_step", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("mfa_enabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("mfa_challenge_hash", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("mfa_challenge_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column("auth_token_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("users", "mfa_enabled", server_default=None)
    op.alter_column("users", "auth_token_version", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "auth_token_version")
    op.drop_column("users", "mfa_challenge_expires_at")
    op.drop_column("users", "mfa_challenge_hash")
    op.drop_column("users", "mfa_enabled_at")
    op.drop_column("users", "mfa_last_used_step")
    op.drop_column("users", "mfa_recovery_codes_encrypted")
    op.drop_column("users", "mfa_secret_encrypted")
    op.drop_column("users", "mfa_enabled")

