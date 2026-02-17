"""initial schema

Revision ID: b8f1dfd2b70c
Revises:
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8f1dfd2b70c"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_reset_token", sa.String(255), nullable=True),
        sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_verification_token", sa.String(255), nullable=True),
        sa.Column("preferences", sa.Text(), nullable=True),
    )

    # campaigns
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("draft", "scheduled", "running", "paused", "completed", "failed", name="campaignstatus"), nullable=False),
        sa.Column("target_sites", sa.JSON(), nullable=True),
        sa.Column("target_count", sa.Integer(), server_default=sa.text("10")),
        sa.Column("profile_template", sa.JSON(), nullable=True),
        sa.Column("submissions_completed", sa.Integer(), server_default=sa.text("0")),
        sa.Column("submissions_failed", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_execution", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_execution", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # lookup_results
    op.create_table(
        "lookup_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("first_name", sa.String(100), nullable=False, index=True),
        sa.Column("last_name", sa.String(100), nullable=False, index=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(50), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("sources_searched", sa.Integer(), server_default=sa.text("0")),
        sa.Column("sources_successful", sa.Integer(), server_default=sa.text("0")),
        sa.Column("total_records_found", sa.Integer(), server_default=sa.text("0")),
        sa.Column("raw_results", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # person_records
    op.create_table(
        "person_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("lookup_result_id", sa.Integer(), sa.ForeignKey("lookup_results.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source", sa.String(100), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("addresses", sa.JSON(), nullable=True),
        sa.Column("phone_numbers", sa.JSON(), nullable=True),
        sa.Column("emails", sa.JSON(), nullable=True),
        sa.Column("relatives", sa.JSON(), nullable=True),
        sa.Column("profile_url", sa.Text(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # submissions
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("site", sa.String(100), nullable=False, index=True),
        sa.Column("status", sa.Enum("pending", "submitted", "confirmed", "failed", "skipped", name="submissionstatus"), nullable=False),
        sa.Column("profile_data", sa.JSON(), nullable=True),
        sa.Column("reference_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("submissions")
    op.drop_table("person_records")
    op.drop_table("lookup_results")
    op.drop_table("campaigns")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS campaignstatus")
    op.execute("DROP TYPE IF EXISTS submissionstatus")
