"""add target identity to campaigns

Revision ID: a3c7e91f4d2b
Revises: b8f1dfd2b70c
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a3c7e91f4d2b"
down_revision: Union[str, None] = "b8f1dfd2b70c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("target_first_name", sa.String(100), nullable=True))
    op.add_column("campaigns", sa.Column("target_last_name", sa.String(100), nullable=True))
    op.add_column("campaigns", sa.Column("target_city", sa.String(100), nullable=True))
    op.add_column("campaigns", sa.Column("target_state", sa.String(2), nullable=True))
    op.add_column("campaigns", sa.Column("target_age", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "target_age")
    op.drop_column("campaigns", "target_state")
    op.drop_column("campaigns", "target_city")
    op.drop_column("campaigns", "target_last_name")
    op.drop_column("campaigns", "target_first_name")
