from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_active_user
from app.modules.dashboard.schemas import (
    DashboardOverviewEnvelope,
    DashboardSummaryEnvelope,
    PatientActiveItemsEnvelope,
    PatientDetailsEnvelope,
)
from app.modules.dashboard.services import (
    get_dashboard_overview,
    get_dashboard_summary,
    get_patient_active_items,
    get_patient_details,
)

router = APIRouter(dependencies=[Depends(get_current_active_user)])
patient_router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.get("/summary", response_model=DashboardSummaryEnvelope, summary="Get dashboard summary")
def get_summary(
    db: Annotated[Session, Depends(get_db)],
) -> DashboardSummaryEnvelope:
    return DashboardSummaryEnvelope(data=get_dashboard_summary(db))


@router.get("/overview", response_model=DashboardOverviewEnvelope, summary="Get dashboard overview")
def get_overview(
    db: Annotated[Session, Depends(get_db)],
) -> DashboardOverviewEnvelope:
    return DashboardOverviewEnvelope(data=get_dashboard_overview(db))


@patient_router.get(
    "/{patient_id}/details",
    response_model=PatientDetailsEnvelope,
    summary="Get patient details for admin panel",
)
def get_patient_details_route(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PatientDetailsEnvelope:
    return PatientDetailsEnvelope(data=get_patient_details(db, patient_id))


@patient_router.get(
    "/{patient_id}/active-items",
    response_model=PatientActiveItemsEnvelope,
    summary="Get patient active items for admin panel",
)
def get_patient_active_items_route(
    patient_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PatientActiveItemsEnvelope:
    items = get_patient_active_items(db, patient_id)
    return PatientActiveItemsEnvelope(data=items, total=len(items))
