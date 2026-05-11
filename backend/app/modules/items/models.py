from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID as UUIDValue

from sqlalchemy import Boolean, Enum as SqlEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.internal_alerts.models import Alert
    from app.modules.inventory.models import InventoryMovement
    from app.modules.measurement_units.models import Unit
    from app.modules.prescriptions.models import Prescription


class ItemType(str, Enum):
    MEDICATION = "medication"
    SUPPLY = "supply"


class Item(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "items"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    item_type: Mapped[ItemType] = mapped_column(
        SqlEnum(ItemType, name="item_type_enum", native_enum=False),
        nullable=False,
    )
    unit_id: Mapped[UUIDValue] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    unit: Mapped["Unit"] = relationship(back_populates="items")
    prescriptions: Mapped[list["Prescription"]] = relationship(back_populates="item")
    inventory_movements: Mapped[list["InventoryMovement"]] = relationship(back_populates="item")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="item")
