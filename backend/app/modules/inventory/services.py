from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.clock import (
    get_current_datetime,
    normalize_datetime_to_project_timezone,
)
from app.modules.inventory.models import (
    InventoryAdjustmentOperation,
    InventoryMovement,
    InventoryMovementType,
)
from app.modules.inventory.schemas import InventoryMovementCreate
from app.modules.items.models import Item
from app.modules.patients.models import Patient
from app.modules.prescriptions.models import Prescription


def calculate_inventory_stock_effect(
    movement_type: InventoryMovementType,
    quantity: Decimal,
    adjustment_operation: InventoryAdjustmentOperation | None = None,
) -> Decimal:
    if movement_type == InventoryMovementType.ENTRY:
        return quantity
    if movement_type in {
        InventoryMovementType.ADMINISTRATION,
        InventoryMovementType.LOSS,
        InventoryMovementType.DISCARD,
    }:
        return quantity * Decimal("-1")
    if adjustment_operation == InventoryAdjustmentOperation.INCREASE:
        return quantity
    return quantity * Decimal("-1")


def build_stock_balance_expression():
    return case(
        (
            InventoryMovement.movement_type == InventoryMovementType.ENTRY,
            InventoryMovement.quantity,
        ),
        (
            InventoryMovement.movement_type == InventoryMovementType.ADMINISTRATION,
            -InventoryMovement.quantity,
        ),
        (
            InventoryMovement.movement_type == InventoryMovementType.LOSS,
            -InventoryMovement.quantity,
        ),
        (
            InventoryMovement.movement_type == InventoryMovementType.DISCARD,
            -InventoryMovement.quantity,
        ),
        (
            and_(
                InventoryMovement.movement_type == InventoryMovementType.ADJUSTMENT,
                InventoryMovement.adjustment_operation == InventoryAdjustmentOperation.INCREASE,
            ),
            InventoryMovement.quantity,
        ),
        else_=-InventoryMovement.quantity,
    )


def get_item_for_inventory_or_raise(db: Session, item_id: UUID, *, require_active: bool) -> Item:
    statement = select(Item).options(selectinload(Item.unit)).where(Item.id == item_id)
    item = db.scalar(statement)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item nao encontrado.",
        )
    if require_active and not item.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nao e possivel movimentar estoque de item inativo.",
        )
    return item


def get_patient_for_inventory_or_raise(db: Session, patient_id: UUID) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente nao encontrado.",
        )
    return patient


def get_prescription_for_inventory_or_raise(db: Session, prescription_id: UUID) -> Prescription:
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescricao nao encontrada.",
        )
    return prescription


def validate_inventory_relationships(
    db: Session,
    payload: InventoryMovementCreate,
) -> tuple[Item, UUID | None, UUID | None]:
    item = get_item_for_inventory_or_raise(db, payload.item_id, require_active=True)
    resolved_patient_id = payload.patient_id
    resolved_prescription_id = payload.prescription_id

    if payload.patient_id is not None:
        get_patient_for_inventory_or_raise(db, payload.patient_id)

    if payload.prescription_id is not None:
        prescription = get_prescription_for_inventory_or_raise(db, payload.prescription_id)
        if prescription.item_id != payload.item_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A prescricao informada nao pertence ao item enviado.",
            )
        if resolved_patient_id is None:
            resolved_patient_id = prescription.patient_id
        elif resolved_patient_id != prescription.patient_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O paciente informado nao corresponde a prescricao enviada.",
            )

    if payload.movement_type == InventoryMovementType.ADMINISTRATION and resolved_patient_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Movimentacoes do tipo administration exigem patient_id ou prescription_id.",
        )

    if (
        payload.movement_type == InventoryMovementType.ADMINISTRATION
        and resolved_patient_id is not None
        and resolved_prescription_id is None
    ):
        resolved_prescription_id = _resolve_prescription_id_for_administration(
            db,
            patient_id=resolved_patient_id,
            item_id=payload.item_id,
            occurred_at=payload.occurred_at,
        )

    return item, resolved_patient_id, resolved_prescription_id


def _resolve_prescription_id_for_administration(
    db: Session,
    *,
    patient_id: UUID,
    item_id: UUID,
    occurred_at: datetime | None,
) -> UUID | None:
    effective_occurrence = get_current_datetime(current_datetime=occurred_at)
    localized_occurrence = normalize_datetime_to_project_timezone(
        effective_occurrence
    )
    occurrence_date = localized_occurrence.date()

    statement = (
        select(Prescription)
        .where(Prescription.patient_id == patient_id)
        .where(Prescription.item_id == item_id)
        .where(Prescription.is_active.is_(True))
        .where(Prescription.start_date <= occurrence_date)
        .where(
            (Prescription.end_date.is_(None)) | (Prescription.end_date >= occurrence_date)
        )
        .order_by(Prescription.start_date.desc(), Prescription.created_at.desc())
    )
    matching_prescriptions = list(db.scalars(statement).all())
    if len(matching_prescriptions) == 1:
        return matching_prescriptions[0].id
    return None


def create_inventory_movement(
    db: Session,
    payload: InventoryMovementCreate,
    *,
    created_by_user_id: UUID,
) -> InventoryMovement:
    item, resolved_patient_id, resolved_prescription_id = validate_inventory_relationships(
        db,
        payload,
    )

    movement_data = {
        "item_id": payload.item_id,
        "unit_id": item.unit_id,
        "patient_id": resolved_patient_id,
        "prescription_id": resolved_prescription_id,
        "created_by_user_id": created_by_user_id,
        "movement_type": payload.movement_type,
        "adjustment_operation": payload.adjustment_operation,
        "quantity": payload.quantity,
        "reason": payload.reason,
        "notes": payload.notes,
    }
    if payload.occurred_at is not None:
        movement_data["occurred_at"] = payload.occurred_at

    movement = InventoryMovement(
        **movement_data,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


def list_inventory_movements(
    db: Session,
    *,
    item_id: UUID | None = None,
    patient_id: UUID | None = None,
    prescription_id: UUID | None = None,
    movement_type: InventoryMovementType | None = None,
) -> list[InventoryMovement]:
    statement = select(InventoryMovement).order_by(
        InventoryMovement.occurred_at.desc(),
        InventoryMovement.created_at.desc(),
    )

    if item_id is not None:
        statement = statement.where(InventoryMovement.item_id == item_id)
    if patient_id is not None:
        statement = statement.where(InventoryMovement.patient_id == patient_id)
    if prescription_id is not None:
        statement = statement.where(InventoryMovement.prescription_id == prescription_id)
    if movement_type is not None:
        statement = statement.where(InventoryMovement.movement_type == movement_type)

    return list(db.scalars(statement).all())


def get_inventory_stock_effect(movement: InventoryMovement) -> Decimal:
    return calculate_inventory_stock_effect(
        movement.movement_type,
        movement.quantity,
        movement.adjustment_operation,
    )


def calculate_current_stock_for_item(db: Session, item_id: UUID) -> Decimal:
    stock_expression = build_stock_balance_expression()
    statement = select(func.coalesce(func.sum(stock_expression), 0)).where(
        InventoryMovement.item_id == item_id
    )
    current_stock = db.scalar(statement)
    if isinstance(current_stock, Decimal):
        return current_stock
    return Decimal(str(current_stock))


def get_item_stock_summary(db: Session, item_id: UUID) -> tuple[Item, Decimal]:
    item = get_item_for_inventory_or_raise(db, item_id, require_active=False)
    current_stock = calculate_current_stock_for_item(db, item_id)
    return item, current_stock
