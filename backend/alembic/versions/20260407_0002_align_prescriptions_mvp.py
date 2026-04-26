"""align prescriptions to mvp contract

Revision ID: 20260407_0002
Revises: 20260407_0001
Create Date: 2026-04-07 00:02:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260407_0002"
down_revision = "20260407_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("prescriptions", sa.Column("dose_amount", sa.Numeric(14, 3), nullable=True))
    op.add_column("prescriptions", sa.Column("frequency_per_day", sa.Integer(), nullable=True))
    op.add_column("prescriptions", sa.Column("specific_times", sa.JSON(), nullable=True))
    op.add_column(
        "prescriptions",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.execute("UPDATE prescriptions SET dose_amount = dosage_quantity")
    op.execute(
        """
        UPDATE prescriptions
        SET frequency_per_day = CASE
            WHEN frequency ~ '^[0-9]+$' THEN GREATEST(frequency::integer, 1)
            ELSE 1
        END
        """
    )
    op.execute(
        """
        UPDATE prescriptions
        SET is_active = CASE
            WHEN status = 'active' THEN true
            ELSE false
        END
        """
    )

    op.alter_column("prescriptions", "dose_amount", nullable=False)
    op.alter_column("prescriptions", "frequency_per_day", nullable=False)

    op.drop_index(op.f("ix_prescriptions_prescribed_by_user_id"), table_name="prescriptions")
    op.drop_index(op.f("ix_prescriptions_unit_id"), table_name="prescriptions")
    op.drop_constraint(
        op.f("fk_prescriptions_prescribed_by_user_id_users"),
        "prescriptions",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_prescriptions_unit_id_units"),
        "prescriptions",
        type_="foreignkey",
    )

    op.drop_column("prescriptions", "dosage_quantity")
    op.drop_column("prescriptions", "frequency")
    op.drop_column("prescriptions", "unit_id")
    op.drop_column("prescriptions", "prescribed_by_user_id")
    op.drop_column("prescriptions", "notes")
    op.drop_column("prescriptions", "status")


def downgrade() -> None:
    op.add_column("prescriptions", sa.Column("status", sa.String(length=9), nullable=True))
    op.add_column("prescriptions", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("prescriptions", sa.Column("prescribed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("prescriptions", sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("prescriptions", sa.Column("frequency", sa.String(length=100), nullable=True))
    op.add_column("prescriptions", sa.Column("dosage_quantity", sa.Numeric(14, 3), nullable=True))

    op.execute("UPDATE prescriptions SET dosage_quantity = dose_amount")
    op.execute("UPDATE prescriptions SET frequency = frequency_per_day::text")
    op.execute(
        """
        UPDATE prescriptions
        SET status = CASE
            WHEN is_active = true THEN 'active'
            ELSE 'cancelled'
        END
        """
    )
    op.execute(
        """
        UPDATE prescriptions p
        SET unit_id = i.unit_id
        FROM items i
        WHERE p.item_id = i.id
        """
    )

    op.alter_column("prescriptions", "dosage_quantity", nullable=False)
    op.alter_column("prescriptions", "frequency", nullable=False)
    op.alter_column("prescriptions", "unit_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_prescriptions_unit_id_units"),
        "prescriptions",
        "units",
        ["unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_prescriptions_prescribed_by_user_id_users"),
        "prescriptions",
        "users",
        ["prescribed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_prescriptions_prescribed_by_user_id"),
        "prescriptions",
        ["prescribed_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_prescriptions_unit_id"),
        "prescriptions",
        ["unit_id"],
        unique=False,
    )

    op.drop_column("prescriptions", "is_active")
    op.drop_column("prescriptions", "specific_times")
    op.drop_column("prescriptions", "frequency_per_day")
    op.drop_column("prescriptions", "dose_amount")
