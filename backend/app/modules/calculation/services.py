from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session

from app.core.clock import get_current_date
from app.modules.calculation.core.basic import build_basic_calculation_payload
from app.modules.calculation.core.calculation import (
    build_availability_snapshot,
    build_metrics_snapshot,
    quantize_quantity,
)
from app.modules.calculation.core.dose_schedule import (
    classify_dose_day_status,
    DoseAdministrationRecord,
    build_fixed_dose_occurrences,
    summarize_dose_occurrences,
)
from app.modules.calculation.core.divergence import build_divergence_snapshot
from app.modules.calculation.core.sources import (
    CalculationSourceRow,
    fetch_calculation_source_rows,
)
from app.modules.calculation.core.status import build_status_context_snapshot
from app.modules.calculation.core.timing import (
    resolve_reference_datetime,
)
from app.modules.calculation.core.usage_modes import (
    resolve_expected_consumption_for_plan,
    resolve_usage_mode_plan,
)
from app.modules.calculation.schemas import (
    CalculationAdministrationDayStatus,
    CalculationDoseOccurrence,
    CalculationDoseOccurrenceState,
    CalculationDoseScheduleSummary,
    CalculationAlertSyncResponse,
    CalculationBatchPayload,
    CalculationEnginePayload,
    CalculationOperationalStatus,
    CalculationItemPayload,
    PatientDoseScheduleEntry,
    PatientDoseScheduleResponse,
    PatientConsumptionSummaryResponse,
)
from app.modules.internal_alerts import services as internal_alert_services
from app.modules.inventory.models import InventoryMovement, InventoryMovementType
from app.modules.inventory.services import calculate_current_stock_for_item
from app.modules.items.models import Item
from app.modules.patients.models import Patient
from app.modules.prescriptions.models import Prescription

DEFAULT_REALIZED_WINDOW_DAYS = 7
MAX_REALIZED_WINDOW_DAYS = 30


def validate_window_days(window_days: int) -> int:
    if window_days < 1 or window_days > MAX_REALIZED_WINDOW_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"window_days deve estar entre 1 e {MAX_REALIZED_WINDOW_DAYS} para o MVP."
            ),
        )
    return window_days


def _get_patient_or_raise(db: Session, patient_id: UUID) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente nao encontrado.",
        )
    return patient


def _get_item_or_raise(db: Session, item_id: UUID) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item nao encontrado.",
        )
    return item


def _list_active_prescriptions_for_patient_item(
    db: Session,
    *,
    patient_id: UUID,
    item_id: UUID,
    reference_date: date,
) -> list[Prescription]:
    statement = (
        select(Prescription)
        .where(Prescription.patient_id == patient_id)
        .where(Prescription.item_id == item_id)
        .where(Prescription.is_active.is_(True))
        .where(Prescription.start_date <= reference_date)
        .where(
            or_(
                Prescription.end_date.is_(None),
                Prescription.end_date >= reference_date,
            )
        )
        .order_by(Prescription.start_date.desc(), Prescription.created_at.desc())
    )
    return list(db.scalars(statement).all())


def _list_active_projection_pairs(
    db: Session,
    *,
    reference_date: date,
    patient_id: UUID | None = None,
    item_id: UUID | None = None,
) -> list[tuple[UUID, UUID]]:
    statement = (
        select(
            distinct(Prescription.patient_id).label("patient_id"),
            Prescription.item_id.label("item_id"),
        )
        .join(Patient, Patient.id == Prescription.patient_id)
        .join(Item, Item.id == Prescription.item_id)
        .where(Prescription.is_active.is_(True))
        .where(Patient.is_active.is_(True))
        .where(Item.is_active.is_(True))
        .where(Prescription.start_date <= reference_date)
        .where(
            or_(
                Prescription.end_date.is_(None),
                Prescription.end_date >= reference_date,
            )
        )
        .order_by(Prescription.patient_id.asc(), Prescription.item_id.asc())
    )

    if patient_id is not None:
        statement = statement.where(Prescription.patient_id == patient_id)
    if item_id is not None:
        statement = statement.where(Prescription.item_id == item_id)

    rows = db.execute(statement).all()
    return [(row.patient_id, row.item_id) for row in rows]


def _calculate_actual_consumption_until_now(
    db: Session,
    *,
    patient_id: UUID,
    item_id: UUID,
    window_start: datetime | None,
    window_end: datetime | None,
) -> Decimal | None:
    if window_start is None or window_end is None:
        return None

    start_datetime_utc = window_start.astimezone(timezone.utc)
    end_datetime_utc = window_end.astimezone(timezone.utc)

    statement = (
        select(func.coalesce(func.sum(InventoryMovement.quantity), 0))
        .where(InventoryMovement.patient_id == patient_id)
        .where(InventoryMovement.item_id == item_id)
        .where(InventoryMovement.movement_type == InventoryMovementType.ADMINISTRATION)
        .where(InventoryMovement.occurred_at >= start_datetime_utc)
        .where(InventoryMovement.occurred_at <= end_datetime_utc)
    )
    result = db.scalar(statement)
    if isinstance(result, Decimal):
        return result
    return Decimal(str(result))


def _list_administration_records_until_now(
    db: Session,
    *,
    patient_id: UUID,
    item_id: UUID,
    window_start: datetime | None,
    window_end: datetime | None,
) -> list[DoseAdministrationRecord]:
    if window_start is None or window_end is None:
        return []

    start_datetime_utc = window_start.astimezone(timezone.utc)
    end_datetime_utc = window_end.astimezone(timezone.utc)

    statement = (
        select(InventoryMovement)
        .where(InventoryMovement.patient_id == patient_id)
        .where(InventoryMovement.item_id == item_id)
        .where(InventoryMovement.movement_type == InventoryMovementType.ADMINISTRATION)
        .where(InventoryMovement.occurred_at >= start_datetime_utc)
        .where(InventoryMovement.occurred_at <= end_datetime_utc)
        .order_by(InventoryMovement.occurred_at.asc(), InventoryMovement.created_at.asc())
    )
    records = list(db.scalars(statement).all())
    return [
        DoseAdministrationRecord(
            occurred_at=record.occurred_at.astimezone(window_end.tzinfo),
            quantity=record.quantity,
            prescription_id=record.prescription_id,
        )
        for record in records
    ]


def _build_payload_from_source(
    source: CalculationSourceRow,
    *,
    reference_date: date,
    window_days: int,
) -> CalculationItemPayload:
    metrics = build_metrics_snapshot(source, window_days=window_days)
    divergence = build_divergence_snapshot(metrics)
    status_context = build_status_context_snapshot(metrics, divergence)
    availability = build_availability_snapshot(
        metrics,
        divergence_available=divergence.comparable,
        status_context_available=status_context.ready_for_status_classification,
    )

    return CalculationItemPayload(
        reference_date=reference_date,
        item_id=source.item_id,
        item_name=source.item_name,
        item_type=source.item_type,
        unit_id=source.unit_id,
        unit_symbol=source.unit_symbol,
        availability=availability,
        metrics=metrics,
        divergence=divergence,
        status_context=status_context,
    )


def build_basic_patient_item_calculation(
    db: Session,
    *,
    patient_id: UUID,
    item_id: UUID,
    reference_date: date | None = None,
    reference_datetime: datetime | None = None,
) -> CalculationEnginePayload:
    resolved_reference_date = reference_date or get_current_date()
    resolved_reference_datetime = resolve_reference_datetime(
        reference_date=resolved_reference_date,
        reference_datetime=reference_datetime,
    )
    patient = _get_patient_or_raise(db, patient_id)
    item = _get_item_or_raise(db, item_id)
    prescriptions = _list_active_prescriptions_for_patient_item(
        db,
        patient_id=patient_id,
        item_id=item_id,
        reference_date=resolved_reference_date,
    )
    usage_plan = resolve_usage_mode_plan(
        prescriptions,
        reference_datetime=resolved_reference_datetime,
    )
    dose_occurrences: list[CalculationDoseOccurrence] | None = None
    dose_schedule: CalculationDoseScheduleSummary | None = None
    administration_day_status: CalculationAdministrationDayStatus | None = None
    administration_day_reason: str | None = None
    if usage_plan.use_dose_occurrences:
        administration_records = _list_administration_records_until_now(
            db,
            patient_id=patient.id,
            item_id=item.id,
            window_start=usage_plan.actual_window_start,
            window_end=usage_plan.actual_window_end,
        )
        evaluated_occurrences = build_fixed_dose_occurrences(
            prescriptions,
            administration_records=administration_records,
            reference_datetime=resolved_reference_datetime,
        )
        occurrence_summary = summarize_dose_occurrences(evaluated_occurrences)
        day_status_summary = classify_dose_day_status(evaluated_occurrences)
        expected_consumption_until_now = occurrence_summary.expected_chargeable_quantity
        actual_consumption_until_now = occurrence_summary.completed_quantity
        administration_day_status = day_status_summary.status
        administration_day_reason = day_status_summary.reason
        dose_occurrences = [
            CalculationDoseOccurrence(
                scheduled_at=occurrence.scheduled_at,
                tolerated_until=occurrence.tolerated_until,
                dose_amount=quantize_quantity(occurrence.dose_amount),
                state=CalculationDoseOccurrenceState(occurrence.state.value),
                prescription_id=occurrence.prescription_id,
                matched_occurred_at=occurrence.matched_occurred_at,
            )
            for occurrence in evaluated_occurrences
        ]
        dose_schedule = _build_dose_schedule_summary(dose_occurrences)
    else:
        actual_consumption_until_now = _calculate_actual_consumption_until_now(
            db,
            patient_id=patient.id,
            item_id=item.id,
            window_start=usage_plan.actual_window_start,
            window_end=usage_plan.actual_window_end,
        )
        expected_consumption_until_now = resolve_expected_consumption_for_plan(
            usage_plan,
            actual_consumption_until_now=actual_consumption_until_now,
        )
        if usage_plan.schedule_invalid_reason is not None:
            administration_day_status = CalculationAdministrationDayStatus.INVALID_SCHEDULE
            administration_day_reason = usage_plan.schedule_invalid_reason
    current_stock = calculate_current_stock_for_item(db, item_id)

    return build_basic_calculation_payload(
        reference_date=resolved_reference_date,
        patient_id=patient.id,
        patient_name=patient.full_name,
        item_id=item.id,
        item_name=item.name,
        unit_symbol=item.unit.symbol if item.unit is not None else "",
        usage_mode=usage_plan.usage_mode,
        comparison_window=usage_plan.comparison_window,
        min_expected_per_day=usage_plan.minimum_expected_per_day,
        max_expected_per_day=usage_plan.maximum_expected_per_day,
        daily_consumption=usage_plan.daily_consumption,
        current_stock=current_stock,
        expected_consumption_until_now=expected_consumption_until_now,
        actual_consumption_until_now=actual_consumption_until_now,
        dose_occurrences=dose_occurrences,
        dose_schedule=dose_schedule,
        administration_day_status=administration_day_status,
        administration_day_reason=administration_day_reason,
        adherence_expected=usage_plan.adherence_expected,
        invalid_reason_override=(
            administration_day_reason
            if administration_day_status == CalculationAdministrationDayStatus.INVALID_SCHEDULE
            else usage_plan.invalid_reason
        ),
    )


def _operational_status_order(status: CalculationOperationalStatus) -> int:
    order = {
        CalculationOperationalStatus.INVALID_PRESCRIPTION: 0,
        CalculationOperationalStatus.INCONSISTENT_DATA: 1,
        CalculationOperationalStatus.CRITICAL_STOCK: 2,
        CalculationOperationalStatus.LOW_STOCK: 3,
        CalculationOperationalStatus.CONSUMPTION_ABOVE_EXPECTED: 4,
        CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED: 5,
        CalculationOperationalStatus.OK: 6,
    }
    return order[status]


def build_patient_consumption_summary(
    db: Session,
    patient_id: UUID,
    *,
    reference_date: date | None = None,
) -> PatientConsumptionSummaryResponse:
    resolved_reference_date = reference_date or get_current_date()
    patient = _get_patient_or_raise(db, patient_id)
    pairs = _list_active_projection_pairs(
        db,
        reference_date=resolved_reference_date,
        patient_id=patient_id,
    )

    items = [
        build_basic_patient_item_calculation(
            db,
            patient_id=pair_patient_id,
            item_id=pair_item_id,
            reference_date=resolved_reference_date,
        )
        for pair_patient_id, pair_item_id in pairs
    ]
    sorted_items = sorted(
        items,
        key=lambda item: (
            _operational_status_order(item.status),
            item.item_name.lower(),
        ),
    )

    return PatientConsumptionSummaryResponse(
        patient_id=patient.id,
        patient_name=patient.full_name,
        items=sorted_items,
        total_items=len(sorted_items),
        items_requiring_attention=sum(1 for item in sorted_items if item.should_alert),
        invalid_items=sum(1 for item in sorted_items if not item.is_valid),
    )


def _build_dose_schedule_summary(
    dose_occurrences: list[CalculationDoseOccurrence],
) -> CalculationDoseScheduleSummary:
    total_doses = len(dose_occurrences)
    completed_dose_count = sum(
        1
        for occurrence in dose_occurrences
        if occurrence.state == CalculationDoseOccurrenceState.COMPLETED
    )
    due_now_dose_count = sum(
        1
        for occurrence in dose_occurrences
        if occurrence.state == CalculationDoseOccurrenceState.DUE_NOW
    )
    overdue_dose_count = sum(
        1
        for occurrence in dose_occurrences
        if occurrence.state == CalculationDoseOccurrenceState.OVERDUE
    )
    not_due_yet_dose_count = sum(
        1
        for occurrence in dose_occurrences
        if occurrence.state == CalculationDoseOccurrenceState.NOT_DUE_YET
    )

    next_dose = next(
        (
            occurrence
            for occurrence in dose_occurrences
            if occurrence.state
            in {
                CalculationDoseOccurrenceState.DUE_NOW,
                CalculationDoseOccurrenceState.NOT_DUE_YET,
            }
        ),
        None,
    )
    overdue_dose = next(
        (
            occurrence
            for occurrence in dose_occurrences
            if occurrence.state == CalculationDoseOccurrenceState.OVERDUE
        ),
        None,
    )

    return CalculationDoseScheduleSummary(
        total_doses=total_doses,
        completed_dose_count=completed_dose_count,
        due_now_dose_count=due_now_dose_count,
        overdue_dose_count=overdue_dose_count,
        not_due_yet_dose_count=not_due_yet_dose_count,
        next_dose=next_dose,
        overdue_dose=overdue_dose,
    )


def build_patient_dose_schedule(
    db: Session,
    patient_id: UUID,
    *,
    reference_date: date | None = None,
) -> PatientDoseScheduleResponse:
    resolved_reference_date = reference_date or get_current_date()
    patient = _get_patient_or_raise(db, patient_id)
    pairs = _list_active_projection_pairs(
        db,
        reference_date=resolved_reference_date,
        patient_id=patient_id,
    )

    item_projections = [
        build_basic_patient_item_calculation(
            db,
            patient_id=pair_patient_id,
            item_id=pair_item_id,
            reference_date=resolved_reference_date,
        )
        for pair_patient_id, pair_item_id in pairs
    ]

    doses: list[PatientDoseScheduleEntry] = []
    for projection in item_projections:
        for occurrence in projection.dose_occurrences or []:
            doses.append(
                PatientDoseScheduleEntry(
                    patient_id=projection.patient_id,
                    patient_name=projection.patient_name,
                    item_id=projection.item_id,
                    item_name=projection.item_name,
                    unit_symbol=projection.unit_symbol,
                    usage_mode=projection.usage_mode,
                    comparison_window=projection.comparison_window,
                    administration_day_status=projection.administration_day_status,
                    administration_day_reason=projection.administration_day_reason,
                    scheduled_at=occurrence.scheduled_at,
                    tolerated_until=occurrence.tolerated_until,
                    dose_amount=occurrence.dose_amount,
                    state=occurrence.state,
                    prescription_id=occurrence.prescription_id,
                    matched_occurred_at=occurrence.matched_occurred_at,
                )
            )

    sorted_doses = sorted(
        doses,
        key=lambda dose: (
            dose.scheduled_at,
            dose.item_name.lower(),
        ),
    )

    next_dose = next(
        (
            dose
            for dose in sorted_doses
            if dose.state
            in {
                CalculationDoseOccurrenceState.DUE_NOW,
                CalculationDoseOccurrenceState.NOT_DUE_YET,
            }
        ),
        None,
    )
    overdue_doses = [
        dose
        for dose in sorted_doses
        if dose.state == CalculationDoseOccurrenceState.OVERDUE
    ]

    return PatientDoseScheduleResponse(
        patient_id=patient.id,
        patient_name=patient.full_name,
        reference_date=resolved_reference_date,
        doses=sorted_doses,
        total_doses=len(sorted_doses),
        completed_dose_count=sum(
            1
            for dose in sorted_doses
            if dose.state == CalculationDoseOccurrenceState.COMPLETED
        ),
        due_now_dose_count=sum(
            1
            for dose in sorted_doses
            if dose.state == CalculationDoseOccurrenceState.DUE_NOW
        ),
        overdue_dose_count=len(overdue_doses),
        not_due_yet_dose_count=sum(
            1
            for dose in sorted_doses
            if dose.state == CalculationDoseOccurrenceState.NOT_DUE_YET
        ),
        next_dose=next_dose,
        overdue_doses=overdue_doses,
    )


def _should_evaluate_projection_for_alert(
    projection: CalculationEnginePayload,
) -> bool:
    critical_statuses = {
        CalculationOperationalStatus.CRITICAL_STOCK,
        CalculationOperationalStatus.INCONSISTENT_DATA,
        CalculationOperationalStatus.INVALID_PRESCRIPTION,
    }
    return projection.should_alert or projection.status in critical_statuses


def list_alert_candidate_projections(
    db: Session,
    *,
    reference_date: date | None = None,
    limit: int | None = 20,
) -> list[CalculationEnginePayload]:
    sorted_projections = list_projection_payloads(
        db,
        reference_date=reference_date,
        only_alerts=True,
    )
    if limit is None:
        return sorted_projections
    return sorted_projections[:limit]


def list_projection_payloads(
    db: Session,
    *,
    reference_date: date | None = None,
    patient_id: UUID | None = None,
    item_id: UUID | None = None,
    only_alerts: bool = False,
) -> list[CalculationEnginePayload]:
    resolved_reference_date = reference_date or get_current_date()
    pairs = _list_active_projection_pairs(
        db,
        reference_date=resolved_reference_date,
        patient_id=patient_id,
        item_id=item_id,
    )

    projections = [
        build_basic_patient_item_calculation(
            db,
            patient_id=pair_patient_id,
            item_id=pair_item_id,
            reference_date=resolved_reference_date,
        )
        for pair_patient_id, pair_item_id in pairs
    ]

    filtered_projections = projections
    if only_alerts:
        filtered_projections = [
            projection
            for projection in filtered_projections
            if _should_evaluate_projection_for_alert(projection)
        ]

    return sorted(
        filtered_projections,
        key=lambda projection: (
            _operational_status_order(projection.status),
            projection.patient_name.lower(),
            projection.item_name.lower(),
        ),
    )


def sync_calculation_alerts(
    db: Session,
    *,
    reference_date: date | None = None,
) -> CalculationAlertSyncResponse:
    resolved_reference_date = reference_date or get_current_date()
    candidates = list_alert_candidate_projections(
        db,
        reference_date=resolved_reference_date,
        limit=None,
    )
    return internal_alert_services.sync_calculation_projection_alerts(
        db,
        projections=candidates,
        reference_date=resolved_reference_date,
    )


def build_item_calculation_payload(
    db: Session,
    item_id: UUID,
    *,
    reference_date: date | None = None,
    window_days: int = DEFAULT_REALIZED_WINDOW_DAYS,
) -> CalculationItemPayload:
    resolved_reference_date = reference_date or get_current_date()
    validated_window_days = validate_window_days(window_days)
    rows = fetch_calculation_source_rows(
        db,
        reference_date=resolved_reference_date,
        window_days=validated_window_days,
        item_id=item_id,
        include_inactive=True,
    )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item nao encontrado.",
        )

    return _build_payload_from_source(
        rows[0],
        reference_date=resolved_reference_date,
        window_days=validated_window_days,
    )


def build_calculation_batch_payload(
    db: Session,
    *,
    reference_date: date | None = None,
    window_days: int = DEFAULT_REALIZED_WINDOW_DAYS,
    include_inactive: bool = False,
) -> CalculationBatchPayload:
    resolved_reference_date = reference_date or get_current_date()
    validated_window_days = validate_window_days(window_days)
    rows = fetch_calculation_source_rows(
        db,
        reference_date=resolved_reference_date,
        window_days=validated_window_days,
        include_inactive=include_inactive,
    )

    payloads = [
        _build_payload_from_source(
            source,
            reference_date=resolved_reference_date,
            window_days=validated_window_days,
        )
        for source in rows
    ]

    return CalculationBatchPayload(
        reference_date=resolved_reference_date,
        realized_window_days=validated_window_days,
        data=payloads,
        total=len(payloads),
    )
