from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser, get_current_active_user
from app.modules.inventory.models import InventoryMovement, InventoryMovementType
from app.modules.inventory.schemas import (
    InventoryMovementCreate,
    InventoryMovementDetailEnvelope,
    InventoryMovementListEnvelope,
    InventoryMovementResponse,
    ItemStockDetailEnvelope,
    ItemStockResponse,
)
from app.modules.inventory.services import (
    create_inventory_movement,
    get_inventory_stock_effect,
    get_item_stock_summary,
    list_inventory_movements,
)

router = APIRouter(dependencies=[Depends(get_current_active_user)])
stock_router = APIRouter(dependencies=[Depends(get_current_active_user)])


def build_inventory_movement_response(movement: InventoryMovement) -> InventoryMovementResponse:
    return InventoryMovementResponse(
        id=movement.id,
        item_id=movement.item_id,
        unit_id=movement.unit_id,
        patient_id=movement.patient_id,
        prescription_id=movement.prescription_id,
        created_by_user_id=movement.created_by_user_id,
        movement_type=movement.movement_type,
        adjustment_operation=movement.adjustment_operation,
        quantity=movement.quantity,
        stock_effect=get_inventory_stock_effect(movement),
        reason=movement.reason,
        notes=movement.notes,
        occurred_at=movement.occurred_at,
        created_at=movement.created_at,
        updated_at=movement.updated_at,
    )


@router.post(
    "/movements",
    response_model=InventoryMovementDetailEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Create inventory movement",
)
def create_inventory_movement_route(
    payload: InventoryMovementCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> InventoryMovementDetailEnvelope:
    movement = create_inventory_movement(
        db,
        payload,
        created_by_user_id=current_user.id,
    )
    return InventoryMovementDetailEnvelope(data=build_inventory_movement_response(movement))


@router.get("/movements", response_model=InventoryMovementListEnvelope, summary="List inventory movements")
def get_inventory_movements(
    db: Annotated[Session, Depends(get_db)],
    item_id: UUID | None = Query(default=None),
    patient_id: UUID | None = Query(default=None),
    prescription_id: UUID | None = Query(default=None),
    movement_type: InventoryMovementType | None = Query(default=None),
) -> InventoryMovementListEnvelope:
    movements = list_inventory_movements(
        db,
        item_id=item_id,
        patient_id=patient_id,
        prescription_id=prescription_id,
        movement_type=movement_type,
    )
    return InventoryMovementListEnvelope(
        data=[build_inventory_movement_response(movement) for movement in movements],
        total=len(movements),
    )


@stock_router.get("/{item_id}/stock", response_model=ItemStockDetailEnvelope, summary="Get current stock by item")
def get_item_stock(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> ItemStockDetailEnvelope:
    item, current_stock = get_item_stock_summary(db, item_id)
    return ItemStockDetailEnvelope(
        data=ItemStockResponse(
            item_id=item.id,
            item_name=item.name,
            item_type=item.item_type,
            unit_id=item.unit_id,
            unit_name=item.unit.name,
            unit_symbol=item.unit.symbol,
            current_stock=current_stock,
            minimum_stock=item.minimum_stock,
            is_below_minimum=current_stock < item.minimum_stock,
        )
    )
