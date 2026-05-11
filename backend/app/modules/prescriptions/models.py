from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID as UUIDValue

from sqlalchemy import Date, ForeignKey, Integer, JSON, Numeric, Boolean
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.inventory.models import InventoryMovement
    from app.modules.items.models import Item
    from app.modules.patients.models import Patient


class PrescriptionUsageMode(str, Enum):
    FIXED = "fixed"
    VARIABLE = "variable"
    # ON_DEMAND replaces a separate is_prn flag to avoid redundant state.
    ON_DEMAND = "on_demand"


class PrescriptionComparisonWindow(str, Enum):
    SCHEDULED_TIMES = "scheduled_times"
    DAILY_TOTAL = "daily_total"
    SHIFT_WINDOW = "shift_window"
    ROLLING_24H = "rolling_24h"


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class Prescription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prescriptions"

    patient_id: Mapped[UUIDValue] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[UUIDValue] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    dose_amount: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    frequency_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    specific_times: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    # These fields live on the prescription because the same item can be fixed
    # for one patient and on-demand or variable for another.
    usage_mode: Mapped[PrescriptionUsageMode] = mapped_column(
        SqlEnum(
            PrescriptionUsageMode,
            name="prescription_usage_mode_enum",
            native_enum=False,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=PrescriptionUsageMode.FIXED,
        server_default=PrescriptionUsageMode.FIXED.value,
    )
    comparison_window: Mapped[PrescriptionComparisonWindow] = mapped_column(
        SqlEnum(
            PrescriptionComparisonWindow,
            name="prescription_comparison_window_enum",
            native_enum=False,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=PrescriptionComparisonWindow.DAILY_TOTAL,
        server_default=PrescriptionComparisonWindow.DAILY_TOTAL.value,
    )
    min_expected_per_day: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 3),
        nullable=True,
    )
    max_expected_per_day: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 3),
        nullable=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    patient: Mapped["Patient"] = relationship(back_populates="prescriptions")
    item: Mapped["Item"] = relationship(back_populates="prescriptions")
    inventory_movements: Mapped[list["InventoryMovement"]] = relationship(
        back_populates="prescription"
    )
