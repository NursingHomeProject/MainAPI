from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.clock import get_current_datetime
from app.modules.inventory.models import InventoryMovement, InventoryMovementType
from app.modules.inventory.services import build_stock_balance_expression
from app.modules.items.models import Item, ItemType
from app.modules.measurement_units.models import Unit
from app.modules.patients.models import Patient
from app.modules.prescriptions.models import Prescription


@dataclass(slots=True)
class CalculationSourceRow:
    item_id: UUID
    item_name: str
    item_type: ItemType
    unit_id: UUID
    unit_symbol: str
    current_stock: Decimal
    minimum_stock: Decimal
    active_prescriptions: int
    predicted_daily_consumption: Decimal
    realized_total_administration: Decimal


def _to_decimal(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def build_stock_subquery():
    stock_expression = build_stock_balance_expression()
    return (
        select(
            InventoryMovement.item_id.label("item_id"),
            func.coalesce(func.sum(stock_expression), 0).label("current_stock"),
        )
        .group_by(InventoryMovement.item_id)
        .subquery()
    )


def build_predicted_consumption_subquery(reference_date: date):
    return (
        select(
            Prescription.item_id.label("item_id"),
            func.count(Prescription.id).label("active_prescriptions"),
            func.coalesce(
                func.sum(Prescription.dose_amount * Prescription.frequency_per_day),
                0,
            ).label("predicted_daily_consumption"),
        )
        .join(Patient, Patient.id == Prescription.patient_id)
        .where(Prescription.is_active.is_(True))
        .where(Patient.is_active.is_(True))
        .where(Prescription.start_date <= reference_date)
        .where(
            or_(
                Prescription.end_date.is_(None),
                Prescription.end_date >= reference_date,
            )
        )
        .group_by(Prescription.item_id)
        .subquery()
    )


def build_realized_consumption_subquery(window_days: int):
    window_start = get_current_datetime().astimezone(timezone.utc) - timedelta(
        days=window_days
    )
    return (
        select(
            InventoryMovement.item_id.label("item_id"),
            func.coalesce(func.sum(InventoryMovement.quantity), 0).label(
                "realized_total_administration"
            ),
        )
        .where(InventoryMovement.movement_type == InventoryMovementType.ADMINISTRATION)
        .where(InventoryMovement.occurred_at >= window_start)
        .group_by(InventoryMovement.item_id)
        .subquery()
    )


def fetch_calculation_source_rows(
    db: Session,
    *,
    reference_date: date,
    window_days: int,
    item_id: UUID | None = None,
    include_inactive: bool = False,
) -> list[CalculationSourceRow]:
    stock_subquery = build_stock_subquery()
    predicted_subquery = build_predicted_consumption_subquery(reference_date)
    realized_subquery = build_realized_consumption_subquery(window_days)

    statement = (
        select(
            Item.id.label("item_id"),
            Item.name.label("item_name"),
            Item.item_type,
            Item.unit_id,
            Unit.symbol.label("unit_symbol"),
            func.coalesce(stock_subquery.c.current_stock, 0).label("current_stock"),
            Item.minimum_stock,
            func.coalesce(predicted_subquery.c.active_prescriptions, 0).label(
                "active_prescriptions"
            ),
            func.coalesce(
                predicted_subquery.c.predicted_daily_consumption,
                0,
            ).label("predicted_daily_consumption"),
            func.coalesce(
                realized_subquery.c.realized_total_administration,
                0,
            ).label("realized_total_administration"),
        )
        .join(Unit, Unit.id == Item.unit_id)
        .outerjoin(stock_subquery, stock_subquery.c.item_id == Item.id)
        .outerjoin(predicted_subquery, predicted_subquery.c.item_id == Item.id)
        .outerjoin(realized_subquery, realized_subquery.c.item_id == Item.id)
        .order_by(Item.name.asc())
    )

    if item_id is not None:
        statement = statement.where(Item.id == item_id)
    if not include_inactive:
        statement = statement.where(Item.is_active.is_(True))

    rows = db.execute(statement).all()
    return [
        CalculationSourceRow(
            item_id=row.item_id,
            item_name=row.item_name,
            item_type=row.item_type,
            unit_id=row.unit_id,
            unit_symbol=row.unit_symbol,
            current_stock=_to_decimal(row.current_stock),
            minimum_stock=_to_decimal(row.minimum_stock),
            active_prescriptions=int(row.active_prescriptions or 0),
            predicted_daily_consumption=_to_decimal(row.predicted_daily_consumption),
            realized_total_administration=_to_decimal(row.realized_total_administration),
        )
        for row in rows
    ]
