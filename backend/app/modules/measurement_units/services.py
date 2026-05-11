from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.items.models import Item
from app.modules.measurement_units.models import Unit
from app.modules.measurement_units.schemas import UnitCreate, UnitUpdate

DEFAULT_UNITS: tuple[dict[str, str], ...] = (
    {"name": "comprimido", "symbol": "comprimido", "description": "Unidade para comprimidos."},
    {"name": "ml", "symbol": "ml", "description": "Unidade de volume em mililitros."},
    {"name": "unidade", "symbol": "unidade", "description": "Unidade generica para itens diversos."},
)


def list_units(db: Session, *, include_inactive: bool = False) -> list[Unit]:
    statement = select(Unit).order_by(Unit.name.asc(), Unit.created_at.asc())
    if not include_inactive:
        statement = statement.where(Unit.is_active.is_(True))
    return list(db.scalars(statement).all())


def get_unit_by_id(db: Session, unit_id: UUID) -> Unit | None:
    return db.get(Unit, unit_id)


def get_unit_by_name(db: Session, name: str) -> Unit | None:
    normalized_name = name.strip().lower()
    statement = select(Unit).where(func.lower(Unit.name) == normalized_name)
    return db.scalar(statement)


def get_unit_by_symbol(db: Session, symbol: str) -> Unit | None:
    normalized_symbol = symbol.strip().lower()
    statement = select(Unit).where(func.lower(Unit.symbol) == normalized_symbol)
    return db.scalar(statement)


def ensure_unit_uniqueness(
    db: Session,
    *,
    name: str,
    symbol: str,
    exclude_unit_id: UUID | None = None,
) -> None:
    existing_unit_by_name = get_unit_by_name(db, name)
    if existing_unit_by_name and existing_unit_by_name.id != exclude_unit_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ja existe uma unidade com este nome.",
        )

    existing_unit_by_symbol = get_unit_by_symbol(db, symbol)
    if existing_unit_by_symbol and existing_unit_by_symbol.id != exclude_unit_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ja existe uma unidade com este simbolo.",
        )


def create_unit(db: Session, payload: UnitCreate) -> Unit:
    ensure_unit_uniqueness(db, name=payload.name, symbol=payload.symbol)
    unit = Unit(
        name=payload.name,
        symbol=payload.symbol,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def update_unit(db: Session, unit: Unit, payload: UnitUpdate) -> Unit:
    update_data = payload.model_dump(exclude_unset=True)

    next_name = update_data.get("name", unit.name)
    next_symbol = update_data.get("symbol", unit.symbol)
    ensure_unit_uniqueness(
        db,
        name=next_name,
        symbol=next_symbol,
        exclude_unit_id=unit.id,
    )

    if update_data.get("is_active") is False:
        ensure_unit_can_be_deactivated(db, unit)

    for field_name, field_value in update_data.items():
        setattr(unit, field_name, field_value)

    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def ensure_unit_can_be_deactivated(db: Session, unit: Unit) -> None:
    statement = (
        select(Item.id)
        .where(Item.unit_id == unit.id)
        .where(Item.is_active.is_(True))
        .limit(1)
    )
    item_in_use = db.scalar(statement)
    if item_in_use is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nao e possivel inativar uma unidade com itens ativos vinculados.",
        )


def deactivate_unit(db: Session, unit: Unit) -> Unit:
    ensure_unit_can_be_deactivated(db, unit)
    unit.is_active = False
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def seed_default_units(db: Session) -> None:
    for payload in DEFAULT_UNITS:
        existing_unit = get_unit_by_symbol(db, payload["symbol"])
        if existing_unit is not None:
            if not existing_unit.is_active:
                existing_unit.is_active = True
                existing_unit.name = payload["name"]
                existing_unit.description = payload["description"]
                db.add(existing_unit)
            continue
        unit = Unit(
            name=payload["name"],
            symbol=payload["symbol"],
            description=payload["description"],
            is_active=True,
        )
        db.add(unit)
    db.commit()
