from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_active_user
from app.modules.prescriptions.schemas import (
    PrescriptionCreate,
    PrescriptionDetailEnvelope,
    PrescriptionListEnvelope,
    PrescriptionMessageEnvelope,
    PrescriptionResponse,
    PrescriptionUpdate,
)
from app.modules.prescriptions.services import (
    create_prescription,
    deactivate_prescription,
    get_patient_by_id_or_raise,
    get_prescription_by_id,
    list_prescriptions_by_patient,
    update_prescription,
)

router = APIRouter(dependencies=[Depends(get_current_active_user)])
patient_router = APIRouter(dependencies=[Depends(get_current_active_user)])


@patient_router.get(
    "/{patient_id}/prescriptions",
    response_model=PrescriptionListEnvelope,
    summary="List prescriptions by patient",
)
def get_patient_prescriptions(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = Query(default=False),
) -> PrescriptionListEnvelope:
    get_patient_by_id_or_raise(db, patient_id)
    prescriptions = list_prescriptions_by_patient(
        db,
        patient_id,
        include_inactive=include_inactive,
    )
    return PrescriptionListEnvelope(
        data=[PrescriptionResponse.model_validate(prescription) for prescription in prescriptions],
        total=len(prescriptions),
    )


@router.post(
    "",
    response_model=PrescriptionDetailEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Create prescription",
)
def create_prescription_route(
    payload: PrescriptionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> PrescriptionDetailEnvelope:
    prescription = create_prescription(db, payload)
    return PrescriptionDetailEnvelope(data=PrescriptionResponse.model_validate(prescription))


@router.put("/{prescription_id}", response_model=PrescriptionDetailEnvelope, summary="Update prescription")
def update_prescription_route(
    prescription_id: UUID,
    payload: PrescriptionUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> PrescriptionDetailEnvelope:
    prescription = get_prescription_by_id(db, prescription_id)
    if prescription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescricao nao encontrada.",
        )

    updated_prescription = update_prescription(db, prescription, payload)
    return PrescriptionDetailEnvelope(data=PrescriptionResponse.model_validate(updated_prescription))


@router.delete(
    "/{prescription_id}",
    response_model=PrescriptionMessageEnvelope,
    summary="Deactivate prescription",
)
def delete_prescription_route(
    prescription_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PrescriptionMessageEnvelope:
    prescription = get_prescription_by_id(db, prescription_id)
    if prescription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescricao nao encontrada.",
        )

    deactivated_prescription = deactivate_prescription(db, prescription)
    return PrescriptionMessageEnvelope(
        message="Prescricao inativada com sucesso.",
        data=PrescriptionResponse.model_validate(deactivated_prescription),
    )
