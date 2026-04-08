"""background processing and tender inputs

Revision ID: 20260408_02
Revises: 20260408_01
Create Date: 2026-04-08 20:10:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260408_02"
down_revision: str | None = "20260408_01"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tender_inputs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_profile_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_value", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("notice_number", sa.String(length=32), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("deadline", sa.String(length=255), nullable=True),
        sa.Column("max_price", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("normalized_payload", sa.JSON(), nullable=False),
        sa.Column("documents", sa.JSON(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_profile_id"], ["company_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("tender_analyses") as batch_op:
        batch_op.add_column(sa.Column("tender_input_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("background_task_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("failure_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("ai_summary_requested", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_foreign_key(
            "fk_tender_analyses_tender_input_id",
            "tender_inputs",
            ["tender_input_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("tender_analyses") as batch_op:
        batch_op.drop_constraint("fk_tender_analyses_tender_input_id", type_="foreignkey")
        batch_op.drop_column("ai_summary_requested")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("failure_reason")
        batch_op.drop_column("background_task_id")
        batch_op.drop_column("tender_input_id")
    op.drop_table("tender_inputs")
