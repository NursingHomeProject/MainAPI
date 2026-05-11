from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_active_user
from app.modules.measurement_units.schemas import (
    UnitCreate,
    UnitDetailEnvelope,
    UnitListEnvelope,
    UnitMessageEnvelope,
    UnitResponse,
    UnitUpdate,
)
from app.modules.measurement_units.services import (
    create_unit,
    deactivate_unit,
    get_unit_by_id,
    list_units,
    update_unit,
)

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.get("", response_model=UnitListEnvelope, summary="List units")
def get_units(
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = Query(default=False),
) -> UnitListEnvelope:
    units = list_units(db, include_inactive=include_inactive)
    return UnitListEnvelope(
        data=[UnitResponse.model_validate(unit) for unit in units],
        total=len(units),
    )


@router.post(
    "",
    response_model=UnitDetailEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Create unit",
)
def create_unit_route(
    payload: UnitCreate,
    db: Annotated[Session, Depends(get_db)],
) -> UnitDetailEnvelope:
    unit = create_unit(db, payload)
    return UnitDetailEnvelope(data=UnitResponse.model_validate(unit))


@router.get("/{unit_id}", response_model=UnitDetailEnvelope, summary="Get unit by id")
def get_unit(
    unit_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> UnitDetailEnvelope:
    unit = get_unit_by_id(db, unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unidade nao encontrada.",
        )
    return UnitDetailEnvelope(data=UnitResponse.model_validate(unit))


@router.put("/{unit_id}", response_model=UnitDetailEnvelope, summary="Update unit")
def update_unit_route(
    unit_id: UUID,
    payload: UnitUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> UnitDetailEnvelope:
    unit = get_unit_by_id(db, unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unidade nao encontrada.",
        )

    updated_unit = update_unit(db, unit, payload)
    return UnitDetailEnvelope(data=UnitResponse.model_validate(updated_unit))


@router.delete("/{unit_id}", response_model=UnitMessageEnvelope, summary="Deactivate unit")
def delete_unit_route(
    unit_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> UnitMessageEnvelope:
    unit = get_unit_by_id(db, unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unidade nao encontrada.",
        )

    deactivated_unit = deactivate_unit(db, unit)
    return UnitMessageEnvelope(
        message="Unidade inativada com sucesso.",
        data=UnitResponse.model_validate(deactivated_unit),
    )
