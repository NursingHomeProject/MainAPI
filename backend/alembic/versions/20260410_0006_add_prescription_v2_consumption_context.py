"""add prescription v2 consumption context

Revision ID: 20260410_0006
Revises: 20260410_0005
Create Date: 2026-04-10 12:20:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260410_0006"
down_revision = "20260410_0005"
branch_labels = None
depends_on = None


prescription_usage_mode_enum = sa.Enum(
    "fixed",
    "variable",
    "on_demand",
    name="prescription_usage_mode_enum",
    native_enum=False,
)

prescription_comparison_window_enum = sa.Enum(
    "scheduled_times",
    "daily_total",
    "shift_window",
    "rolling_24h",
    name="prescription_comparison_window_enum",
    native_enum=False,
)


def upgrade() -> None:
    op.add_column(
        "prescriptions",
        sa.Column(
            "usage_mode",
            prescription_usage_mode_enum,
            nullable=False,
            server_default="fixed",
        ),
    )
    op.add_column(
        "prescriptions",
        sa.Column(
            "comparison_window",
            prescription_comparison_window_enum,
            nullable=False,
            server_default="daily_total",
        ),
    )
    op.add_column(
        "prescriptions",
        sa.Column("min_expected_per_day", sa.Numeric(14, 3), nullable=True),
    )
    op.add_column(
        "prescriptions",
        sa.Column("max_expected_per_day", sa.Numeric(14, 3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prescriptions", "max_expected_per_day")
    op.drop_column("prescriptions", "min_expected_per_day")
    op.drop_column("prescriptions", "comparison_window")
    op.drop_column("prescriptions", "usage_mode")
