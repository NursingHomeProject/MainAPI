"""align inventory movements to mvp contract

Revision ID: 20260407_0003
Revises: 20260407_0002
Create Date: 2026-04-07 00:03:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260407_0003"
down_revision = "20260407_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "inventory_movements",
        "movement_type",
        existing_type=sa.String(length=10),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
    op.add_column(
        "inventory_movements",
        sa.Column("adjustment_operation", sa.String(length=10), nullable=True),
    )
    op.execute(
        """
        UPDATE inventory_movements
        SET movement_type = 'administration'
        WHERE movement_type = 'exit'
        """
    )
    op.execute(
        """
        UPDATE inventory_movements
        SET adjustment_operation = 'increase'
        WHERE movement_type = 'adjustment' AND adjustment_operation IS NULL
        """
    )
    op.create_check_constraint(
        "quantity_positive",
        "inventory_movements",
        "quantity > 0",
    )
    op.create_check_constraint(
        "movement_type_valid",
        "inventory_movements",
        "movement_type IN ('entry', 'administration', 'loss', 'adjustment', 'discard')",
    )
    op.create_check_constraint(
        "adjustment_operation_valid",
        "inventory_movements",
        "(adjustment_operation IS NULL OR adjustment_operation IN ('increase', 'decrease'))",
    )
    op.create_check_constraint(
        "adjustment_required",
        "inventory_movements",
        "((movement_type = 'adjustment' AND adjustment_operation IS NOT NULL) "
        "OR (movement_type <> 'adjustment' AND adjustment_operation IS NULL))",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_inventory_movements_adjustment_required",
        "inventory_movements",
        type_="check",
    )
    op.drop_constraint(
        "ck_inventory_movements_adjustment_operation_valid",
        "inventory_movements",
        type_="check",
    )
    op.drop_constraint(
        "ck_inventory_movements_movement_type_valid",
        "inventory_movements",
        type_="check",
    )
    op.drop_constraint(
        "ck_inventory_movements_quantity_positive",
        "inventory_movements",
        type_="check",
    )
    op.execute(
        """
        UPDATE inventory_movements
        SET movement_type = 'exit'
        WHERE movement_type = 'administration'
        """
    )
    op.drop_column("inventory_movements", "adjustment_operation")
    op.alter_column(
        "inventory_movements",
        "movement_type",
        existing_type=sa.String(length=20),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
