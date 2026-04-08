"""organizations and authentication

Revision ID: 20260408_03
Revises: 20260408_02
Create Date: 2026-04-08 23:30:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260408_03"
down_revision: str | None = "20260408_02"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("password_salt", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_foreign_key(
            "fk_users_organization_id",
            "organizations",
            ["organization_id"],
            ["id"],
        )

    with op.batch_alter_table("company_profiles") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_company_profiles_organization_id",
            "organizations",
            ["organization_id"],
            ["id"],
        )

    with op.batch_alter_table("tender_inputs") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_tender_inputs_organization_id",
            "organizations",
            ["organization_id"],
            ["id"],
        )

    with op.batch_alter_table("tender_analyses") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_tender_analyses_organization_id",
            "organizations",
            ["organization_id"],
            ["id"],
        )

    connection = op.get_bind()
    now_expression = sa.text("CURRENT_TIMESTAMP")
    connection.execute(
        sa.text(
            """
            INSERT INTO organizations (name, slug, is_active, created_at, updated_at)
            VALUES ('Default organization', 'default-organization', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        )
    )
    default_organization_id = connection.execute(
        sa.text("SELECT id FROM organizations WHERE slug = 'default-organization'")
    ).scalar_one()

    connection.execute(
        sa.text(
            """
            UPDATE users
            SET organization_id = COALESCE(organization_id, :organization_id),
                password_hash = COALESCE(password_hash, ''),
                password_salt = COALESCE(password_salt, '')
            """
        ),
        {"organization_id": default_organization_id},
    )

    connection.execute(
        sa.text(
            """
            UPDATE company_profiles
            SET organization_id = COALESCE(
                organization_id,
                (SELECT users.organization_id FROM users WHERE users.id = company_profiles.user_id),
                :organization_id
            )
            """
        ),
        {"organization_id": default_organization_id},
    )

    connection.execute(
        sa.text(
            """
            UPDATE tender_inputs
            SET organization_id = COALESCE(
                organization_id,
                (SELECT company_profiles.organization_id
                 FROM company_profiles
                 WHERE company_profiles.id = tender_inputs.company_profile_id),
                :organization_id
            )
            """
        ),
        {"organization_id": default_organization_id},
    )

    connection.execute(
        sa.text(
            """
            UPDATE tender_analyses
            SET organization_id = COALESCE(
                organization_id,
                (SELECT company_profiles.organization_id
                 FROM company_profiles
                 WHERE company_profiles.id = tender_analyses.company_profile_id),
                :organization_id
            )
            """
        ),
        {"organization_id": default_organization_id},
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("organization_id", nullable=False)
        batch_op.alter_column("password_hash", nullable=False)
        batch_op.alter_column("password_salt", nullable=False)

    with op.batch_alter_table("company_profiles") as batch_op:
        batch_op.alter_column("organization_id", nullable=False)

    with op.batch_alter_table("tender_inputs") as batch_op:
        batch_op.alter_column("organization_id", nullable=False)

    with op.batch_alter_table("tender_analyses") as batch_op:
        batch_op.alter_column("organization_id", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("tender_analyses") as batch_op:
        batch_op.drop_constraint("fk_tender_analyses_organization_id", type_="foreignkey")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("tender_inputs") as batch_op:
        batch_op.drop_constraint("fk_tender_inputs_organization_id", type_="foreignkey")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("company_profiles") as batch_op:
        batch_op.drop_constraint("fk_company_profiles_organization_id", type_="foreignkey")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_organization_id", type_="foreignkey")
        batch_op.drop_column("is_owner")
        batch_op.drop_column("password_salt")
        batch_op.drop_column("password_hash")
        batch_op.drop_column("organization_id")

    op.drop_table("organizations")
