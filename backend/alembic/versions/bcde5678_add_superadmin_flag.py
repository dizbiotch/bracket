"""add users.is_superadmin

Revision ID: bcde5678_add_superadmin_flag
Revises: abcd1234players_only
Create Date: 2026-01-17 00:10:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str | None = "bcde5678_add_superadmin_flag"
down_revision: str | None = "abcd1234players_only"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_superadmin", sa.Boolean(), server_default="f", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_superadmin")
