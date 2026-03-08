"""add campaign_type column to campaigns

Revision ID: e4c9a7b2d1f0
Revises: c5d8f2a1e7b3
Create Date: 2026-03-07

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4c9a7b2d1f0"
down_revision: Union[str, None] = "c5d8f2a1e7b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column(
            "campaign_type",
            sa.String(length=20),
            nullable=False,
            server_default="poisoning",
        ),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "campaign_type")
