from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.items.models import Item
from app.modules.patients.models import Patient
from app.modules.prescriptions.models import (
    Prescription,
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)
from app.modules.prescriptions.schemas import PrescriptionCreate, PrescriptionUpdate


def get_patient_by_id_or_raise(db: Session, patient_id: UUID) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente nao encontrado.",
        )
    return patient


def get_active_patient_or_raise(db: Session, patient_id: UUID) -> Patient:
    patient = get_patient_by_id_or_raise(db, patient_id)
    if not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nao e possivel criar prescricao para paciente inativo.",
        )
    return patient


def get_item_or_raise(db: Session, item_id: UUID) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item nao encontrado.",
        )
    if not item.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nao e possivel criar prescricao para item inativo.",
        )
    return item


def validate_prescription_consistency(
    *,
    frequency_per_day: int,
    specific_times: list[str] | None,
    usage_mode: PrescriptionUsageMode,
    comparison_window,
    min_expected_per_day,
    max_expected_per_day,
    start_date,
    end_date,
) -> None:
    if end_date is not None and end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A data final nao pode ser anterior a data inicial.",
        )
    if specific_times is not None and len(specific_times) != frequency_per_day:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A quantidade de horarios deve corresponder a frequencia diaria.",
        )
    if (
        usage_mode == PrescriptionUsageMode.FIXED
        and comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES
        and not specific_times
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Prescricoes fixas com comparacao por horario exigem specific_times.",
        )
    if (
        usage_mode != PrescriptionUsageMode.FIXED
        and comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A janela scheduled_times e reservada para prescricoes fixas.",
        )
    if (
        min_expected_per_day is not None
        and max_expected_per_day is not None
        and max_expected_per_day < min_expected_per_day
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O maximo esperado por dia nao pode ser menor que o minimo.",
        )
    if usage_mode == PrescriptionUsageMode.FIXED and (
        min_expected_per_day is not None or max_expected_per_day is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Faixas esperadas por dia sao usadas apenas em prescricoes variaveis ou sob demanda.",
        )


def list_prescriptions_by_patient(
    db: Session,
    patient_id: UUID,
    *,
    include_inactive: bool = False,
) -> list[Prescription]:
    statement = (
        select(Prescription)
        .where(Prescription.patient_id == patient_id)
        .order_by(
            Prescription.is_active.desc(),
            Prescription.start_date.desc(),
            Prescription.created_at.desc(),
        )
    )
    if not include_inactive:
        statement = statement.where(Prescription.is_active.is_(True))
    return list(db.scalars(statement).all())


def get_prescription_by_id(db: Session, prescription_id: UUID) -> Prescription | None:
    return db.get(Prescription, prescription_id)


def create_prescription(db: Session, payload: PrescriptionCreate) -> Prescription:
    get_active_patient_or_raise(db, payload.patient_id)
    get_item_or_raise(db, payload.item_id)
    validate_prescription_consistency(
        frequency_per_day=payload.frequency_per_day,
        specific_times=payload.specific_times,
        usage_mode=payload.usage_mode,
        comparison_window=payload.comparison_window,
        min_expected_per_day=payload.min_expected_per_day,
        max_expected_per_day=payload.max_expected_per_day,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )

    prescription = Prescription(
        patient_id=payload.patient_id,
        item_id=payload.item_id,
        dose_amount=payload.dose_amount,
        frequency_per_day=payload.frequency_per_day,
        specific_times=payload.specific_times,
        usage_mode=payload.usage_mode,
        comparison_window=payload.comparison_window,
        min_expected_per_day=payload.min_expected_per_day,
        max_expected_per_day=payload.max_expected_per_day,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_active=payload.is_active,
    )
    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    return prescription


def update_prescription(
    db: Session,
    prescription: Prescription,
    payload: PrescriptionUpdate,
) -> Prescription:
    update_data = payload.model_dump(exclude_unset=True)

    next_patient_id = update_data.get("patient_id", prescription.patient_id)
    next_item_id = update_data.get("item_id", prescription.item_id)
    next_frequency = update_data.get("frequency_per_day", prescription.frequency_per_day)
    next_specific_times = update_data.get("specific_times", prescription.specific_times)
    next_usage_mode = update_data.get("usage_mode", prescription.usage_mode)
    next_min_expected = update_data.get(
        "min_expected_per_day",
        prescription.min_expected_per_day,
    )
    next_max_expected = update_data.get(
        "max_expected_per_day",
        prescription.max_expected_per_day,
    )
    next_start_date = update_data.get("start_date", prescription.start_date)
    next_end_date = update_data.get("end_date", prescription.end_date)

    get_active_patient_or_raise(db, next_patient_id)
    get_item_or_raise(db, next_item_id)
    validate_prescription_consistency(
        frequency_per_day=next_frequency,
        specific_times=next_specific_times,
        usage_mode=next_usage_mode,
        comparison_window=update_data.get(
            "comparison_window",
            prescription.comparison_window,
        ),
        min_expected_per_day=next_min_expected,
        max_expected_per_day=next_max_expected,
        start_date=next_start_date,
        end_date=next_end_date,
    )

    for field_name, field_value in update_data.items():
        setattr(prescription, field_name, field_value)

    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    return prescription


def deactivate_prescription(db: Session, prescription: Prescription) -> Prescription:
    prescription.is_active = False
    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    return prescription
