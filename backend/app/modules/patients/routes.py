from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_active_user
from app.modules.patients.schemas import (
    PatientCreate,
    PatientDetailEnvelope,
    PatientListEnvelope,
    PatientMessageEnvelope,
    PatientResponse,
    PatientUpdate,
)
from app.modules.patients.services import (
    create_patient,
    deactivate_patient,
    get_patient_by_id,
    list_patients,
    update_patient,
)

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.get("", response_model=PatientListEnvelope, summary="List patients")
def get_patients(
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = Query(default=False),
) -> PatientListEnvelope:
    patients = list_patients(db, include_inactive=include_inactive)
    return PatientListEnvelope(
        data=[PatientResponse.model_validate(patient) for patient in patients],
        total=len(patients),
    )


@router.post(
    "",
    response_model=PatientDetailEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Create patient",
)
def create_patient_route(
    payload: PatientCreate,
    db: Annotated[Session, Depends(get_db)],
) -> PatientDetailEnvelope:
    patient = create_patient(db, payload)
    return PatientDetailEnvelope(data=PatientResponse.model_validate(patient))


@router.get("/{patient_id}", response_model=PatientDetailEnvelope, summary="Get patient by id")
def get_patient(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PatientDetailEnvelope:
    patient = get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente nao encontrado.",
        )
    return PatientDetailEnvelope(data=PatientResponse.model_validate(patient))


@router.put("/{patient_id}", response_model=PatientDetailEnvelope, summary="Update patient")
def update_patient_route(
    patient_id: UUID,
    payload: PatientUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> PatientDetailEnvelope:
    patient = get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente nao encontrado.",
        )

    updated_patient = update_patient(db, patient, payload)
    return PatientDetailEnvelope(data=PatientResponse.model_validate(updated_patient))


@router.delete(
    "/{patient_id}",
    response_model=PatientMessageEnvelope,
    summary="Deactivate patient",
)
def delete_patient_route(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PatientMessageEnvelope:
    patient = get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente nao encontrado.",
        )

    deactivated_patient = deactivate_patient(db, patient)
    return PatientMessageEnvelope(
        message="Paciente inativado com sucesso.",
        data=PatientResponse.model_validate(deactivated_patient),
    )
