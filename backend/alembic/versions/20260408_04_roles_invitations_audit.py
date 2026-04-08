"""roles invitations and audit logs

Revision ID: 20260408_04
Revises: 20260408_03
Create Date: 2026-04-08 23:55:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260408_04"
down_revision: str | None = "20260408_03"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "role" not in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column("role", sa.String(length=32), nullable=False, server_default="operator")
            )

    connection.execute(
        sa.text(
            """
            UPDATE users
            SET role = CASE
                WHEN is_owner = 1 THEN 'owner'
                ELSE 'operator'
            END
            """
        )
    )

    existing_tables = set(inspector.get_table_names())

    if "organization_invitations" not in existing_tables:
        op.create_table(
            "organization_invitations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("invited_by_user_id", sa.Integer(), nullable=True),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("token", sa.String(length=255), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token", name="uq_organization_invitations_token"),
        )

    if "audit_logs" not in existing_tables:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=120), nullable=False),
            sa.Column("entity_type", sa.String(length=64), nullable=False),
            sa.Column("entity_id", sa.String(length=64), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("organization_invitations")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("role")
