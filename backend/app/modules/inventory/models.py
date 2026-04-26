from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID as UUIDValue

from sqlalchemy import CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.items.models import Item
    from app.modules.measurement_units.models import Unit
    from app.modules.patients.models import Patient
    from app.modules.prescriptions.models import Prescription


class InventoryMovementType(str, Enum):
    ENTRY = "entry"
    ADMINISTRATION = "administration"
    LOSS = "loss"
    ADJUSTMENT = "adjustment"
    DISCARD = "discard"


class InventoryAdjustmentOperation(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"


def _enum_values(enum_class: type[Enum]) -> list[str]:
    return [member.value for member in enum_class]


class InventoryMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "movement_type IN ('entry', 'administration', 'loss', 'adjustment', 'discard')",
            name="movement_type_valid",
        ),
        CheckConstraint(
            "(adjustment_operation IS NULL OR adjustment_operation IN ('increase', 'decrease'))",
            name="adjustment_operation_valid",
        ),
        CheckConstraint(
            "((movement_type = 'adjustment' AND adjustment_operation IS NOT NULL) "
            "OR (movement_type <> 'adjustment' AND adjustment_operation IS NULL))",
            name="adjustment_required",
        ),
    )

    item_id: Mapped[UUIDValue] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    unit_id: Mapped[UUIDValue] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[UUIDValue | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prescription_id: Mapped[UUIDValue | None] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[UUIDValue | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    movement_type: Mapped[InventoryMovementType] = mapped_column(
        SqlEnum(
            InventoryMovementType,
            name="inventory_movement_type_enum",
            native_enum=False,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    adjustment_operation: Mapped[InventoryAdjustmentOperation | None] = mapped_column(
        SqlEnum(
            InventoryAdjustmentOperation,
            name="inventory_adjustment_operation_enum",
            native_enum=False,
            values_callable=_enum_values,
        ),
        nullable=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    item: Mapped["Item"] = relationship(back_populates="inventory_movements")
    unit: Mapped["Unit"] = relationship(back_populates="inventory_movements")
    patient: Mapped["Patient | None"] = relationship(back_populates="inventory_movements")
    prescription: Mapped["Prescription | None"] = relationship(
        back_populates="inventory_movements"
    )
    created_by: Mapped["User | None"] = relationship(back_populates="inventory_movements")
