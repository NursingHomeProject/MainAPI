from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.modules.patients.models import Patient
from app.modules.patients.schemas import PatientCreate, PatientUpdate


def _apply_active_filter(statement: Select[tuple[Patient]], include_inactive: bool) -> Select[tuple[Patient]]:
    if include_inactive:
        return statement
    return statement.where(Patient.is_active.is_(True))


def list_patients(db: Session, *, include_inactive: bool = False) -> list[Patient]:
    statement = select(Patient).order_by(Patient.full_name.asc(), Patient.created_at.asc())
    statement = _apply_active_filter(statement, include_inactive)
    return list(db.scalars(statement).all())


def get_patient_by_id(db: Session, patient_id: UUID) -> Patient | None:
    return db.get(Patient, patient_id)


def create_patient(db: Session, payload: PatientCreate) -> Patient:
    patient = Patient(
        full_name=payload.full_name,
        birth_date=payload.birth_date,
        care_notes=payload.care_notes,
        is_active=payload.is_active,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def update_patient(db: Session, patient: Patient, payload: PatientUpdate) -> Patient:
    update_data = payload.model_dump(exclude_unset=True)
    for field_name, field_value in update_data.items():
        setattr(patient, field_name, field_value)

    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def deactivate_patient(db: Session, patient: Patient) -> Patient:
    patient.is_active = False
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient
