"""align alerts to mvp contract

Revision ID: 20260407_0004
Revises: 20260407_0003
Create Date: 2026-04-07 00:04:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260407_0004"
down_revision = "20260407_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("alerts", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        """
        UPDATE alerts
        SET
            resolved_by_user_id = acknowledged_by_user_id,
            resolved_at = COALESCE(acknowledged_at, updated_at)
        WHERE acknowledged_by_user_id IS NOT NULL
           OR acknowledged_at IS NOT NULL
           OR status IN ('acknowledged', 'resolved')
        """
    )
    op.execute(
        """
        UPDATE alerts
        SET status = 'resolved'
        WHERE status = 'acknowledged'
        """
    )

    op.create_foreign_key(
        op.f("fk_alerts_resolved_by_user_id_users"),
        "alerts",
        "users",
        ["resolved_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_alerts_resolved_by_user_id"),
        "alerts",
        ["resolved_by_user_id"],
        unique=False,
    )

    op.drop_index(op.f("ix_alerts_acknowledged_by_user_id"), table_name="alerts")
    op.drop_constraint(
        op.f("fk_alerts_acknowledged_by_user_id_users"),
        "alerts",
        type_="foreignkey",
    )
    op.drop_column("alerts", "acknowledged_by_user_id")
    op.drop_column("alerts", "acknowledged_at")


def downgrade() -> None:
    op.add_column("alerts", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alerts", sa.Column("acknowledged_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.execute(
        """
        UPDATE alerts
        SET
            acknowledged_by_user_id = resolved_by_user_id,
            acknowledged_at = resolved_at
        WHERE resolved_by_user_id IS NOT NULL
           OR resolved_at IS NOT NULL
        """
    )

    op.create_foreign_key(
        op.f("fk_alerts_acknowledged_by_user_id_users"),
        "alerts",
        "users",
        ["acknowledged_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_alerts_acknowledged_by_user_id"),
        "alerts",
        ["acknowledged_by_user_id"],
        unique=False,
    )

    op.drop_index(op.f("ix_alerts_resolved_by_user_id"), table_name="alerts")
    op.drop_constraint(
        op.f("fk_alerts_resolved_by_user_id_users"),
        "alerts",
        type_="foreignkey",
    )
    op.drop_column("alerts", "resolved_by_user_id")
    op.drop_column("alerts", "resolved_at")
