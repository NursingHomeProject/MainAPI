from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.modules.internal_alerts.contracts import (
    CALCULATION_ALERT_TYPE,
    build_calculation_alert_contract,
    get_internal_alert_contract,
    try_get_trigger_from_status,
)
from app.modules.internal_alerts.models import Alert, AlertSeverity, AlertStatus
from app.modules.internal_alerts.schemas import (
    AlertCreate,
    AlertSummaryResponse,
)
from app.modules.items.models import Item
from app.modules.patients.models import Patient
from app.modules.prescriptions.models import (
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)

if TYPE_CHECKING:
    from datetime import date

    from app.modules.calculation.schemas import (
        CalculationEnginePayload,
        CalculationOperationalStatus,
    )


class AlertUpsertResult(NamedTuple):
    alert: Alert
    created: bool
    updated: bool


class CalculationAlertCreationAction(str, Enum):
    CREATED = "created"
    REUSED = "reused"
    SKIPPED = "skipped"


class AlertResolutionAction(str, Enum):
    RESOLVED = "resolved"
    ALREADY_RESOLVED = "already_resolved"


class CalculationAlertCreationResult(NamedTuple):
    alert: Alert | None
    action: CalculationAlertCreationAction
    created: bool
    reused: bool
    updated: bool
    reason: str | None


class AlertResolutionResult(NamedTuple):
    alert: Alert
    action: AlertResolutionAction
    changed: bool


def get_alert_by_id(db: Session, alert_id: UUID) -> Alert | None:
    return db.get(Alert, alert_id)


def get_item_for_alert_or_raise(db: Session, item_id: UUID) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item nao encontrado.",
        )
    return item


def get_patient_for_alert_or_raise(db: Session, patient_id: UUID) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente nao encontrado.",
        )
    return patient


def build_alert_severity_order_expression():
    return case(
        (Alert.severity == AlertSeverity.CRITICAL, 3),
        (Alert.severity == AlertSeverity.WARNING, 2),
        else_=1,
    )


def list_alerts(
    db: Session,
    *,
    status_filter: AlertStatus | None = None,
    severity_filter: AlertSeverity | None = None,
    alert_type_filter: str | None = None,
    patient_id: UUID | None = None,
    item_id: UUID | None = None,
) -> list[Alert]:
    severity_order = build_alert_severity_order_expression()
    statement = select(Alert).order_by(
        Alert.status.asc(),
        severity_order.desc(),
        Alert.created_at.desc(),
    )
    if status_filter is not None:
        statement = statement.where(Alert.status == status_filter)
    if severity_filter is not None:
        statement = statement.where(Alert.severity == severity_filter)
    if alert_type_filter is not None:
        statement = statement.where(Alert.alert_type == alert_type_filter)
    if patient_id is not None:
        statement = statement.where(Alert.patient_id == patient_id)
    if item_id is not None:
        statement = statement.where(Alert.item_id == item_id)
    return list(db.scalars(statement).all())


def list_open_alerts_by_type(db: Session, *, alert_type: str) -> list[Alert]:
    statement = (
        select(Alert)
        .where(Alert.alert_type == alert_type)
        .where(Alert.status == AlertStatus.OPEN)
        .order_by(Alert.created_at.desc())
    )
    return list(db.scalars(statement).all())


def build_alert_scope_key(
    *,
    alert_type: str,
    patient_id: UUID | None,
    item_id: UUID | None,
) -> tuple[str, UUID | None, UUID | None]:
    return (alert_type, patient_id, item_id)


def extract_alert_primary_reason(value: str) -> str:
    normalized_value = " ".join(value.split()).strip()
    if not normalized_value:
        return ""
    primary_reason = normalized_value.split(".", 1)[0].strip()
    return primary_reason.lower()


def derive_alert_reason(payload: AlertCreate) -> str:
    if payload.reason is not None and payload.reason.strip():
        return payload.reason

    normalized_message = " ".join(payload.message.split()).strip()
    if normalized_message:
        primary_reason = normalized_message.split(".", 1)[0].strip()
        if primary_reason:
            return (
                f"{primary_reason}."
                if normalized_message.startswith(f"{primary_reason}.")
                else primary_reason
            )

    return " ".join(payload.title.split()).strip()


def find_equivalent_open_alert(db: Session, payload: AlertCreate) -> Alert | None:
    statement = (
        select(Alert)
        .where(Alert.status == AlertStatus.OPEN)
        .where(Alert.alert_type == payload.alert_type)
        .order_by(Alert.created_at.desc())
    )

    if payload.patient_id is None:
        statement = statement.where(Alert.patient_id.is_(None))
    else:
        statement = statement.where(Alert.patient_id == payload.patient_id)

    if payload.item_id is None:
        statement = statement.where(Alert.item_id.is_(None))
    else:
        statement = statement.where(Alert.item_id == payload.item_id)

    return db.scalars(statement).first()


def create_or_reuse_alert(db: Session, payload: AlertCreate) -> AlertUpsertResult:
    normalized_payload = payload.model_copy(
        update={"reason": derive_alert_reason(payload)}
    )

    if normalized_payload.item_id is not None:
        get_item_for_alert_or_raise(db, normalized_payload.item_id)
    if normalized_payload.patient_id is not None:
        get_patient_for_alert_or_raise(db, normalized_payload.patient_id)

    existing_alert = find_equivalent_open_alert(db, normalized_payload)
    if existing_alert is not None:
        should_update = (
            existing_alert.title != normalized_payload.title
            or existing_alert.reason != normalized_payload.reason
            or existing_alert.message != normalized_payload.message
            or existing_alert.severity != normalized_payload.severity
        )
        if not should_update:
            return AlertUpsertResult(
                alert=existing_alert,
                created=False,
                updated=False,
            )

        updated_alert = update_alert_content(
            db,
            existing_alert,
            title=normalized_payload.title,
            reason=normalized_payload.reason,
            message=normalized_payload.message,
            severity=normalized_payload.severity,
        )
        return AlertUpsertResult(
            alert=updated_alert,
            created=False,
            updated=True,
        )

    created_alert = create_alert(db, normalized_payload)
    return AlertUpsertResult(
        alert=created_alert,
        created=True,
        updated=False,
    )


def build_alert_summary(
    db: Session,
    *,
    status_filter: AlertStatus | None = None,
    severity_filter: AlertSeverity | None = None,
    alert_type_filter: str | None = None,
    patient_id: UUID | None = None,
    item_id: UUID | None = None,
) -> AlertSummaryResponse:
    alerts = list_alerts(
        db,
        status_filter=status_filter,
        severity_filter=severity_filter,
        alert_type_filter=alert_type_filter,
        patient_id=patient_id,
        item_id=item_id,
    )
    return summarize_alerts(alerts)


def summarize_alerts(alerts: Sequence[Alert]) -> AlertSummaryResponse:
    open_total = 0
    resolved_total = 0
    open_critical = 0
    open_warning = 0
    open_info = 0
    calculation_open = 0
    manual_open = 0
    patients_with_open_alerts: set[UUID] = set()
    items_with_open_alerts: set[UUID] = set()

    for alert in alerts:
        if alert.status == AlertStatus.OPEN:
            open_total += 1
            if alert.alert_type == CALCULATION_ALERT_TYPE:
                calculation_open += 1
            else:
                manual_open += 1

            if alert.patient_id is not None:
                patients_with_open_alerts.add(alert.patient_id)
            if alert.item_id is not None:
                items_with_open_alerts.add(alert.item_id)

            if alert.severity == AlertSeverity.CRITICAL:
                open_critical += 1
            elif alert.severity == AlertSeverity.WARNING:
                open_warning += 1
            else:
                open_info += 1
        else:
            resolved_total += 1

    return AlertSummaryResponse(
        open_total=open_total,
        resolved_total=resolved_total,
        open_critical=open_critical,
        open_warning=open_warning,
        open_info=open_info,
        calculation_open=calculation_open,
        manual_open=manual_open,
        patients_with_open_alerts=len(patients_with_open_alerts),
        items_with_open_alerts=len(items_with_open_alerts),
    )


def create_alert(db: Session, payload: AlertCreate) -> Alert:
    if payload.item_id is not None:
        get_item_for_alert_or_raise(db, payload.item_id)
    if payload.patient_id is not None:
        get_patient_for_alert_or_raise(db, payload.patient_id)

    alert = Alert(
        item_id=payload.item_id,
        patient_id=payload.patient_id,
        alert_type=payload.alert_type,
        title=payload.title,
        reason=derive_alert_reason(payload),
        message=payload.message,
        severity=payload.severity,
        status=AlertStatus.OPEN,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def update_alert_content(
    db: Session,
    alert: Alert,
    *,
    title: str,
    reason: str,
    message: str,
    severity: AlertSeverity,
) -> Alert:
    has_changes = False

    if alert.title != title:
        alert.title = title
        has_changes = True
    if alert.reason != reason:
        alert.reason = reason
        has_changes = True
    if alert.message != message:
        alert.message = message
        has_changes = True
    if alert.severity != severity:
        alert.severity = severity
        has_changes = True

    if not has_changes:
        return alert

    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert(
    db: Session,
    alert: Alert,
    *,
    resolved_by_user_id: UUID | None = None,
) -> Alert:
    if alert.status == AlertStatus.RESOLVED:
        return alert

    alert.status = AlertStatus.RESOLVED
    alert.resolved_by_user_id = resolved_by_user_id
    alert.resolved_at = datetime.now(timezone.utc)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert_manually(
    db: Session,
    alert: Alert,
    *,
    resolved_by_user_id: UUID | None = None,
) -> AlertResolutionResult:
    if alert.status == AlertStatus.RESOLVED:
        return AlertResolutionResult(
            alert=alert,
            action=AlertResolutionAction.ALREADY_RESOLVED,
            changed=False,
        )

    resolved_alert = resolve_alert(
        db,
        alert,
        resolved_by_user_id=resolved_by_user_id,
    )
    return AlertResolutionResult(
        alert=resolved_alert,
        action=AlertResolutionAction.RESOLVED,
        changed=True,
    )


def _get_projection_alert_severity(
    projection: "CalculationEnginePayload",
) -> AlertSeverity:
    from app.modules.calculation.schemas import CalculationOperationalStatus

    if (
        projection.usage_mode == PrescriptionUsageMode.VARIABLE
        and projection.status
        in {
            CalculationOperationalStatus.CONSUMPTION_ABOVE_EXPECTED,
            CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED,
        }
    ):
        return AlertSeverity.INFO

    trigger = try_get_trigger_from_status(projection.status)
    if trigger is None:
        return AlertSeverity.WARNING
    return get_internal_alert_contract(trigger).severity


def _build_projection_alert_title(projection: "CalculationEnginePayload") -> str:
    from app.modules.calculation.schemas import CalculationOperationalStatus

    if _is_scheduled_missed_dose_projection(projection):
        return f"Dose atrasada de {projection.item_name}"

    if (
        projection.usage_mode == PrescriptionUsageMode.VARIABLE
        and projection.status == CalculationOperationalStatus.CONSUMPTION_ABOVE_EXPECTED
    ):
        return "Uso acima da faixa esperada"

    if (
        projection.usage_mode == PrescriptionUsageMode.VARIABLE
        and projection.status == CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED
    ):
        return "Uso abaixo da faixa esperada"

    if (
        projection.comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES
        and projection.status == CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED
    ):
        return "Consumo abaixo do previsto na janela atual"

    if (
        projection.comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES
        and projection.status == CalculationOperationalStatus.CONSUMPTION_ABOVE_EXPECTED
    ):
        return "Consumo acima do previsto na janela atual"

    trigger = try_get_trigger_from_status(projection.status)
    if trigger is None:
        return f"Acompanhamento de {projection.item_name}"
    return build_calculation_alert_contract(
        trigger,
        item_name=projection.item_name,
        patient_name=projection.patient_name,
        daily_consumption=str(projection.daily_consumption),
        unit_symbol=projection.unit_symbol,
        reason_override=projection.alert_reason,
    ).title


def _build_projection_alert_message(projection: "CalculationEnginePayload") -> str:
    if _is_scheduled_missed_dose_projection(projection):
        base_reason = _build_scheduled_missed_dose_reason(projection)
        base_message = (
            f"{base_reason} Paciente: {projection.patient_name}. "
            f"Item: {projection.item_name}."
        )
        overdue_context = _build_overdue_dose_context(projection)
        if overdue_context is not None:
            base_message = f"{base_message} {overdue_context}"
        return _append_projection_context_to_message(base_message, projection)

    trigger = try_get_trigger_from_status(projection.status)
    if trigger is None:
        base_reason = projection.alert_reason or "Revise o acompanhamento deste item."
        base_message = (
            f"{base_reason} Paciente: {projection.patient_name}. "
            f"Item: {projection.item_name}. "
            f"Consumo diario previsto: {projection.daily_consumption} {projection.unit_symbol}."
        )
        return _append_projection_context_to_message(base_message, projection)

    rendered_contract = build_calculation_alert_contract(
        trigger,
        item_name=projection.item_name,
        patient_name=projection.patient_name,
        daily_consumption=str(projection.daily_consumption),
        unit_symbol=projection.unit_symbol,
        reason_override=projection.alert_reason,
    )
    return _append_projection_context_to_message(rendered_contract.message, projection)


def _build_scheduled_missed_dose_reason(
    projection: "CalculationEnginePayload",
) -> str:
    if projection.alert_reason is not None and projection.alert_reason.strip():
        return projection.alert_reason
    if (
        projection.administration_day_reason is not None
        and projection.administration_day_reason.strip()
    ):
        return projection.administration_day_reason
    return "Existe dose atrasada sem registro de administracao apos a tolerancia configurada."


def _build_overdue_dose_context(
    projection: "CalculationEnginePayload",
) -> str | None:
    if not projection.dose_occurrences:
        return None

    overdue_times = [
        occurrence.scheduled_at.strftime("%H:%M")
        for occurrence in projection.dose_occurrences
        if occurrence.state.value == "overdue"
    ]
    if not overdue_times:
        return None

    return f"Horario(s) em atraso: {', '.join(overdue_times)}."


def _append_projection_context_to_message(
    base_message: str,
    projection: "CalculationEnginePayload",
) -> str:
    context_parts: list[str] = []
    if projection.current_stock is not None:
        context_parts.append(
            f"Saldo atual: {projection.current_stock} {projection.unit_symbol}."
        )
    if projection.days_remaining is not None:
        context_parts.append(
            f"Cobertura estimada: {projection.days_remaining} dia(s)."
        )
    if projection.divergence is not None:
        context_parts.append(
            f"Divergencia acumulada: {projection.divergence} {projection.unit_symbol}."
        )

    if not context_parts:
        return base_message

    return f"{base_message} {' '.join(context_parts)}"


def _build_alert_payload_from_projection(
    projection: "CalculationEnginePayload",
) -> AlertCreate:
    trigger = try_get_trigger_from_status(projection.status)
    rendered_contract = None
    if trigger is not None:
        rendered_contract = build_calculation_alert_contract(
            trigger,
            item_name=projection.item_name,
            patient_name=projection.patient_name,
            daily_consumption=str(projection.daily_consumption),
            unit_symbol=projection.unit_symbol,
            reason_override=projection.alert_reason,
        )

    return AlertCreate(
        alert_type=CALCULATION_ALERT_TYPE,
        title=_build_projection_alert_title(projection),
        reason=rendered_contract.reason if rendered_contract is not None else projection.alert_reason,
        message=_build_projection_alert_message(projection),
        severity=_get_projection_alert_severity(projection),
        item_id=projection.item_id,
        patient_id=projection.patient_id,
    )


def _should_create_alert_from_projection(
    projection: "CalculationEnginePayload",
) -> bool:
    from app.modules.calculation.schemas import (
        CalculationAdministrationDayStatus,
        CalculationOperationalStatus,
    )

    if projection.usage_mode and projection.usage_mode.value == "on_demand":
        if projection.status in {
            CalculationOperationalStatus.CONSUMPTION_ABOVE_EXPECTED,
            CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED,
        }:
            return False

    if (
        projection.comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES
        and projection.status
        == CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED
    ):
        return (
            projection.administration_day_status
            == CalculationAdministrationDayStatus.MISSED_DOSE
        )

    critical_alert_statuses: set[CalculationOperationalStatus] = {
        CalculationOperationalStatus.CRITICAL_STOCK,
        CalculationOperationalStatus.INCONSISTENT_DATA,
        CalculationOperationalStatus.INVALID_PRESCRIPTION,
    }
    return projection.should_alert or projection.status in critical_alert_statuses


def _is_scheduled_missed_dose_projection(
    projection: "CalculationEnginePayload",
) -> bool:
    from app.modules.calculation.schemas import (
        CalculationAdministrationDayStatus,
        CalculationOperationalStatus,
    )

    return (
        projection.comparison_window == PrescriptionComparisonWindow.SCHEDULED_TIMES
        and projection.status
        == CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED
        and projection.administration_day_status
        == CalculationAdministrationDayStatus.MISSED_DOSE
    )


def create_alert_from_calculation_projection(
    db: Session,
    projection: "CalculationEnginePayload",
) -> CalculationAlertCreationResult:
    if not _should_create_alert_from_projection(projection):
        return CalculationAlertCreationResult(
            alert=None,
            action=CalculationAlertCreationAction.SKIPPED,
            created=False,
            reused=False,
            updated=False,
            reason=projection.alert_reason,
        )

    alert_payload = _build_alert_payload_from_projection(projection)
    upsert_result = create_or_reuse_alert(db, alert_payload)

    if upsert_result.created:
        action = CalculationAlertCreationAction.CREATED
        reused = False
    else:
        action = CalculationAlertCreationAction.REUSED
        reused = True

    return CalculationAlertCreationResult(
        alert=upsert_result.alert,
        action=action,
        created=upsert_result.created,
        reused=reused,
        updated=upsert_result.updated,
        reason=projection.alert_reason,
    )


def deduplicate_open_alerts_by_scope(
    existing_alerts: list[Alert],
) -> tuple[dict[tuple[str, UUID | None, UUID | None], Alert], list[Alert]]:
    unique_alerts: dict[tuple[str, UUID | None, UUID | None], Alert] = {}
    duplicates: list[Alert] = []

    for alert in existing_alerts:
        key = build_alert_scope_key(
            alert_type=alert.alert_type,
            patient_id=alert.patient_id,
            item_id=alert.item_id,
        )
        if key in unique_alerts:
            duplicates.append(alert)
            continue
        unique_alerts[key] = alert

    return unique_alerts, duplicates


def sync_calculation_projection_alerts(
    db: Session,
    *,
    projections: list["CalculationEnginePayload"],
    reference_date: "date",
):
    from app.modules.calculation.schemas import CalculationAlertSyncResponse

    created_count = 0
    updated_count = 0
    unchanged_count = 0
    resolved_count = 0

    active_scope_keys = {
        build_alert_scope_key(
            alert_type=CALCULATION_ALERT_TYPE,
            patient_id=projection.patient_id,
            item_id=projection.item_id,
        )
        for projection in projections
        if _should_create_alert_from_projection(projection)
    }

    for projection in projections:
        creation_result = create_alert_from_calculation_projection(db, projection)
        if creation_result.action == CalculationAlertCreationAction.SKIPPED:
            continue
        if creation_result.created:
            created_count += 1
        elif creation_result.updated:
            updated_count += 1
        else:
            unchanged_count += 1

    existing_open_alerts = list_open_alerts_by_type(
        db,
        alert_type=CALCULATION_ALERT_TYPE,
    )
    unique_open_alerts, duplicate_alerts = deduplicate_open_alerts_by_scope(
        existing_open_alerts
    )

    for duplicate_alert in duplicate_alerts:
        if duplicate_alert.status != AlertStatus.OPEN:
            continue
        resolve_alert(db, duplicate_alert)
        resolved_count += 1

    for scope_key, open_alert in unique_open_alerts.items():
        if scope_key in active_scope_keys:
            continue
        resolve_alert(db, open_alert)
        resolved_count += 1

    return CalculationAlertSyncResponse(
        reference_date=reference_date,
        candidate_total=len(projections),
        created=created_count,
        updated=updated_count,
        resolved=resolved_count,
        unchanged=unchanged_count,
    )
