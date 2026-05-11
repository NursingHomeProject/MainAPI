from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_active_user
from app.modules.calculation.schemas import (
    CalculationAlertSyncEnvelope,
    CalculationEngineEnvelope,
    CalculationEngineListEnvelope,
    CalculationItemProjectionEnvelope,
    PatientDoseScheduleEnvelope,
    PatientConsumptionSummaryEnvelope,
)
from app.modules.calculation.services import (
    DEFAULT_REALIZED_WINDOW_DAYS,
    MAX_REALIZED_WINDOW_DAYS,
    build_basic_patient_item_calculation,
    build_item_calculation_payload,
    build_patient_dose_schedule,
    build_patient_consumption_summary,
    list_alert_candidate_projections,
    sync_calculation_alerts,
)

router = APIRouter(dependencies=[Depends(get_current_active_user)])
patient_router = APIRouter(dependencies=[Depends(get_current_active_user)])
item_router = APIRouter(dependencies=[Depends(get_current_active_user)])


@patient_router.get(
    "/{patient_id}/items/{item_id}/projection",
    response_model=CalculationEngineEnvelope,
    summary="Consultar projecao de consumo de um item do paciente",
)
def get_patient_item_projection(
    patient_id: UUID,
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    reference_date: Annotated[
        date | None,
        Query(description="Data de referencia para o calculo no formato YYYY-MM-DD."),
    ] = None,
) -> CalculationEngineEnvelope:
    return CalculationEngineEnvelope(
        data=build_basic_patient_item_calculation(
            db,
            patient_id=patient_id,
            item_id=item_id,
            reference_date=reference_date,
        )
    )


@patient_router.get(
    "/{patient_id}/consumption-summary",
    response_model=PatientConsumptionSummaryEnvelope,
    summary="Consultar resumo de consumo do paciente",
)
def get_patient_consumption_summary(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    reference_date: Annotated[
        date | None,
        Query(description="Data de referencia para consolidar o resumo no formato YYYY-MM-DD."),
    ] = None,
) -> PatientConsumptionSummaryEnvelope:
    return PatientConsumptionSummaryEnvelope(
        data=build_patient_consumption_summary(
            db,
            patient_id,
            reference_date=reference_date,
        )
    )


@patient_router.get(
    "/{patient_id}/dose-schedule",
    response_model=PatientDoseScheduleEnvelope,
    summary="Consultar agenda diaria de doses do paciente",
)
def get_patient_dose_schedule(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    reference_date: Annotated[
        date | None,
        Query(description="Data de referencia para montar a agenda do dia no formato YYYY-MM-DD."),
    ] = None,
) -> PatientDoseScheduleEnvelope:
    return PatientDoseScheduleEnvelope(
        data=build_patient_dose_schedule(
            db,
            patient_id,
            reference_date=reference_date,
        )
    )


@item_router.get(
    "/{item_id}/projection",
    response_model=CalculationItemProjectionEnvelope,
    summary="Consultar projecao consolidada do item",
)
def get_item_projection(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    reference_date: Annotated[
        date | None,
        Query(description="Data de referencia para o calculo no formato YYYY-MM-DD."),
    ] = None,
    window_days: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_REALIZED_WINDOW_DAYS,
            description="Janela em dias para o consumo realizado recente.",
        ),
    ] = DEFAULT_REALIZED_WINDOW_DAYS,
) -> CalculationItemProjectionEnvelope:
    return CalculationItemProjectionEnvelope(
        data=build_item_calculation_payload(
            db,
            item_id,
            reference_date=reference_date,
            window_days=window_days,
        )
    )


@router.get(
    "/alerts-candidates",
    response_model=CalculationEngineListEnvelope,
    summary="Listar candidatos a alerta do motor de calculo",
)
def get_alert_candidates(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    reference_date: Annotated[
        date | None,
        Query(description="Data de referencia usada para gerar a lista no formato YYYY-MM-DD."),
    ] = None,
) -> CalculationEngineListEnvelope:
    items = list_alert_candidate_projections(
        db,
        reference_date=reference_date,
        limit=limit,
    )
    return CalculationEngineListEnvelope(data=items, total=len(items))


@router.post(
    "/alerts-sync",
    response_model=CalculationAlertSyncEnvelope,
    summary="Sincronizar alertas internos a partir do motor de calculo",
)
def sync_calculation_alerts_route(
    db: Annotated[Session, Depends(get_db)],
    reference_date: Annotated[
        date | None,
        Query(description="Data de referencia usada para sincronizar os alertas no formato YYYY-MM-DD."),
    ] = None,
) -> CalculationAlertSyncEnvelope:
    return CalculationAlertSyncEnvelope(
        data=sync_calculation_alerts(
            db,
            reference_date=reference_date,
        )
    )
