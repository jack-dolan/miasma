"""add campaign baselines table

Revision ID: c5d8f2a1e7b3
Revises: a3c7e91f4d2b
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c5d8f2a1e7b3"
down_revision: Union[str, None] = "a3c7e91f4d2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_baselines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("snapshot_type", sa.String(20), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("sources_checked", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("raw_results", sa.JSON(), nullable=True),
        sa.Column("accuracy_score", sa.Float(), nullable=True),
        sa.Column("data_points_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("data_points_accurate", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_table("campaign_baselines")
