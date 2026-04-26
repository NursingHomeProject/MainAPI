"""add alert reason for minimal traceability

Revision ID: 20260410_0005
Revises: 20260407_0004
Create Date: 2026-04-10 00:05:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260410_0005"
down_revision = "20260407_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alerts",
        sa.Column(
            "reason",
            sa.Text(),
            nullable=True,
            server_default="Motivo nao informado.",
        ),
    )

    op.execute(
        """
        UPDATE alerts
        SET reason = COALESCE(
            NULLIF(BTRIM(SPLIT_PART(message, '.', 1)), ''),
            NULLIF(BTRIM(title), ''),
            'Motivo nao informado.'
        )
        """
    )

    op.alter_column(
        "alerts",
        "reason",
        nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("alerts", "reason")
