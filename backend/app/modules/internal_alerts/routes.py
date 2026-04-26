from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser, get_current_active_user
from app.modules.internal_alerts.models import AlertSeverity, AlertStatus
from app.modules.internal_alerts.schemas import (
    AlertCreate,
    AlertDetailEnvelope,
    AlertListEnvelope,
    AlertMessageEnvelope,
    AlertResponse,
    AlertSummaryEnvelope,
)
from app.modules.internal_alerts.services import (
    build_alert_summary,
    create_or_reuse_alert,
    get_alert_by_id,
    list_alerts,
    resolve_alert_manually,
    summarize_alerts,
)

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.get("", response_model=AlertListEnvelope, summary="List internal alerts")
def get_alerts(
    db: Annotated[Session, Depends(get_db)],
    status_filter: AlertStatus | None = Query(default=None, alias="status"),
    severity_filter: AlertSeverity | None = Query(default=None, alias="severity"),
    alert_type_filter: str | None = Query(default=None, alias="alert_type"),
    patient_id: UUID | None = Query(default=None),
    item_id: UUID | None = Query(default=None),
) -> AlertListEnvelope:
    alerts = list_alerts(
        db,
        status_filter=status_filter,
        severity_filter=severity_filter,
        alert_type_filter=alert_type_filter,
        patient_id=patient_id,
        item_id=item_id,
    )
    return AlertListEnvelope(
        data=[AlertResponse.model_validate(alert) for alert in alerts],
        total=len(alerts),
        summary=summarize_alerts(alerts),
    )


@router.get(
    "/summary",
    response_model=AlertSummaryEnvelope,
    summary="Summarize internal alerts",
)
def get_alerts_summary(
    db: Annotated[Session, Depends(get_db)],
    status_filter: AlertStatus | None = Query(default=None, alias="status"),
    severity_filter: AlertSeverity | None = Query(default=None, alias="severity"),
    alert_type_filter: str | None = Query(default=None, alias="alert_type"),
    patient_id: UUID | None = Query(default=None),
    item_id: UUID | None = Query(default=None),
) -> AlertSummaryEnvelope:
    return AlertSummaryEnvelope(
        data=build_alert_summary(
            db,
            status_filter=status_filter,
            severity_filter=severity_filter,
            alert_type_filter=alert_type_filter,
            patient_id=patient_id,
            item_id=item_id,
        )
    )


@router.post(
    "",
    response_model=AlertDetailEnvelope,
    status_code=status.HTTP_201_CREATED,
    summary="Create internal alert",
)
def create_alert_route(
    payload: AlertCreate,
    db: Annotated[Session, Depends(get_db)],
) -> AlertDetailEnvelope:
    result = create_or_reuse_alert(db, payload)
    return AlertDetailEnvelope(data=AlertResponse.model_validate(result.alert))


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertMessageEnvelope,
    summary="Resolve internal alert",
)
def resolve_alert_route(
    alert_id: UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> AlertMessageEnvelope:
    alert = get_alert_by_id(db, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta nao encontrado.",
        )

    resolution_result = resolve_alert_manually(
        db,
        alert,
        resolved_by_user_id=current_user.id,
    )
    if resolution_result.changed:
        message = "Alerta resolvido com sucesso."
    else:
        message = "Alerta ja estava resolvido."

    return AlertMessageEnvelope(
        message=message,
        action=resolution_result.action.value,
        already_resolved=not resolution_result.changed,
        data=AlertResponse.model_validate(resolution_result.alert),
    )
