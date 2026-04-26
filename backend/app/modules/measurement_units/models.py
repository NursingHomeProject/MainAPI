from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.inventory.models import InventoryMovement
    from app.modules.items.models import Item


class Unit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "units"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    items: Mapped[list["Item"]] = relationship(back_populates="unit")
    inventory_movements: Mapped[list["InventoryMovement"]] = relationship(back_populates="unit")
