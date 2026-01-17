"""add tournaments.players_only

Revision ID: abcd1234players_only
Revises: c1ab44651e79
Create Date: 2026-01-17 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str | None = "abcd1234players_only"
down_revision: str | None = "c1ab44651e79"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "tournaments",
        sa.Column("players_only", sa.Boolean(), server_default="f", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("tournaments", "players_only")
