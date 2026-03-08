"""add removed to submissionstatus enum

Revision ID: f2a6c9d4b8e1
Revises: e4c9a7b2d1f0
Create Date: 2026-03-07

"""

from typing import Sequence, Union

from alembic import op


revision: str = "f2a6c9d4b8e1"
down_revision: Union[str, None] = "e4c9a7b2d1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE submissionstatus ADD VALUE IF NOT EXISTS 'removed'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values directly.
    # Recreate the enum without 'removed', mapping existing rows back to 'skipped'.
    op.execute("ALTER TABLE submissions ALTER COLUMN status TYPE TEXT")
    op.execute("UPDATE submissions SET status = 'skipped' WHERE status = 'removed'")
    op.execute(
        "CREATE TYPE submissionstatus_new AS ENUM "
        "('pending', 'submitted', 'confirmed', 'failed', 'skipped')"
    )
    op.execute(
        "ALTER TABLE submissions ALTER COLUMN status TYPE submissionstatus_new "
        "USING status::submissionstatus_new"
    )
    op.execute("DROP TYPE submissionstatus")
    op.execute("ALTER TYPE submissionstatus_new RENAME TO submissionstatus")
