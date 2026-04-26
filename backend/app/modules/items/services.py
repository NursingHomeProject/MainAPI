from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.items.models import Item
from app.modules.items.schemas import ItemCreate, ItemUpdate
from app.modules.measurement_units.models import Unit


def list_items(db: Session, *, include_inactive: bool = False) -> list[Item]:
    statement = select(Item).order_by(Item.name.asc(), Item.created_at.asc())
    if not include_inactive:
        statement = statement.where(Item.is_active.is_(True))
    return list(db.scalars(statement).all())


def get_item_by_id(db: Session, item_id: UUID) -> Item | None:
    return db.get(Item, item_id)


def get_item_by_name(db: Session, name: str) -> Item | None:
    normalized_name = name.strip().lower()
    statement = select(Item).where(func.lower(Item.name) == normalized_name)
    return db.scalar(statement)


def get_item_by_sku(db: Session, sku: str) -> Item | None:
    normalized_sku = sku.strip().lower()
    statement = select(Item).where(func.lower(Item.sku) == normalized_sku)
    return db.scalar(statement)


def get_active_unit_or_raise(db: Session, unit_id: UUID) -> Unit:
    unit = db.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unidade nao encontrada.",
        )
    if not unit.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nao e possivel vincular item a uma unidade inativa.",
        )
    return unit


def ensure_item_uniqueness(
    db: Session,
    *,
    name: str,
    sku: str | None,
    exclude_item_id: UUID | None = None,
) -> None:
    existing_item_by_name = get_item_by_name(db, name)
    if existing_item_by_name and existing_item_by_name.id != exclude_item_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ja existe um item com este nome.",
        )

    if sku:
        existing_item_by_sku = get_item_by_sku(db, sku)
        if existing_item_by_sku and existing_item_by_sku.id != exclude_item_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ja existe um item com este SKU.",
            )


def create_item(db: Session, payload: ItemCreate) -> Item:
    get_active_unit_or_raise(db, payload.unit_id)
    ensure_item_uniqueness(db, name=payload.name, sku=payload.sku)

    item = Item(
        name=payload.name,
        item_type=payload.item_type,
        unit_id=payload.unit_id,
        description=payload.description,
        sku=payload.sku,
        minimum_stock=payload.minimum_stock,
        is_active=payload.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item: Item, payload: ItemUpdate) -> Item:
    update_data = payload.model_dump(exclude_unset=True)

    next_name = update_data.get("name", item.name)
    next_sku = update_data.get("sku", item.sku)
    ensure_item_uniqueness(
        db,
        name=next_name,
        sku=next_sku,
        exclude_item_id=item.id,
    )

    next_unit_id = update_data.get("unit_id")
    if next_unit_id is not None:
        get_active_unit_or_raise(db, next_unit_id)

    for field_name, field_value in update_data.items():
        setattr(item, field_name, field_value)

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def deactivate_item(db: Session, item: Item) -> Item:
    item.is_active = False
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
