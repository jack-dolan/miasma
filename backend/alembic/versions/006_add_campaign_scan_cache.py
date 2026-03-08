"""add cached scan result fields to campaigns

Revision ID: a9b3c1d7e4f2
Revises: f2a6c9d4b8e1
Create Date: 2026-03-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b3c1d7e4f2"
down_revision: Union[str, None] = "f2a6c9d4b8e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("campaigns", sa.Column("last_scan_result", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "last_scan_result")
    op.drop_column("campaigns", "last_scan_at")
