from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.modules.calculation.schemas import (
    CalculationDivergenceStatus,
    CalculationEnginePayload,
    CalculationOperationalStatus,
)
from app.modules.calculation.services import list_projection_payloads
from app.modules.dashboard.schemas import (
    DashboardCalculationSummary,
    DashboardLowStockItem,
    DashboardOpenAlertItem,
    DashboardOverviewResponse,
    DashboardRecentMovementItem,
    DashboardRiskPatientItem,
    DashboardSummaryResponse,
    PatientActiveItemResponse,
    PatientDetailsAlertItem,
    PatientDetailsMetrics,
    PatientDetailsMovementItem,
    PatientDetailsResponse,
)
from app.modules.internal_alerts.models import Alert, AlertStatus
from app.modules.internal_alerts.services import build_alert_severity_order_expression
from app.modules.inventory.models import (
    InventoryMovement,
)
from app.modules.inventory.services import (
    build_stock_balance_expression,
    calculate_inventory_stock_effect,
)
from app.modules.items.models import Item
from app.modules.measurement_units.models import Unit
from app.modules.patients.models import Patient
from app.modules.prescriptions.models import Prescription

STOCK_RISK_STATUSES = {
    CalculationOperationalStatus.LOW_STOCK,
    CalculationOperationalStatus.CRITICAL_STOCK,
}
CRITICAL_OPERATIONAL_STATUSES = {
    CalculationOperationalStatus.CRITICAL_STOCK,
    CalculationOperationalStatus.INCONSISTENT_DATA,
    CalculationOperationalStatus.INVALID_PRESCRIPTION,
}
DIVERGENCE_OPERATIONAL_STATUSES = {
    CalculationOperationalStatus.CONSUMPTION_ABOVE_EXPECTED,
    CalculationOperationalStatus.CONSUMPTION_BELOW_EXPECTED,
}
RELEVANT_DIVERGENCE_STATUSES = {
    CalculationDivergenceStatus.ABOVE_EXPECTED,
    CalculationDivergenceStatus.BELOW_EXPECTED,
}


def _build_stock_subquery():
    stock_expression = build_stock_balance_expression()
    return (
        select(
            InventoryMovement.item_id.label("item_id"),
            func.coalesce(func.sum(stock_expression), 0).label("current_stock"),
        )
        .group_by(InventoryMovement.item_id)
        .subquery()
    )


def _get_patient_or_raise(db: Session, patient_id: UUID) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente nao encontrado.",
        )
    return patient


def _projection_risk_score(status: CalculationOperationalStatus) -> int:
    if status in CRITICAL_OPERATIONAL_STATUSES:
        return 3
    if status in STOCK_RISK_STATUSES or status in DIVERGENCE_OPERATIONAL_STATUSES:
        return 2
    return 1


def _build_dashboard_calculation_summary(
    projections: list[CalculationEnginePayload],
) -> DashboardCalculationSummary:
    items_at_risk = {
        projection.item_id
        for projection in projections
        if projection.status in STOCK_RISK_STATUSES
    }
    critical_items = {
        projection.item_id
        for projection in projections
        if projection.status == CalculationOperationalStatus.CRITICAL_STOCK
    }
    relevant_divergences = [
        projection
        for projection in projections
        if projection.divergence_status in RELEVANT_DIVERGENCE_STATUSES
    ]
    patients_at_risk = {
        projection.patient_id for projection in projections if projection.should_alert
    }

    return DashboardCalculationSummary(
        items_at_risk=len(items_at_risk),
        critical_items=len(critical_items),
        relevant_divergences=len(relevant_divergences),
        patients_at_risk=len(patients_at_risk),
    )


def _build_dashboard_risk_patients(
    projections: list[CalculationEnginePayload],
) -> list[DashboardRiskPatientItem]:
    patient_buckets: dict[UUID, dict[str, int | str | UUID]] = {}

    for projection in projections:
        if not projection.should_alert:
            continue

        bucket = patient_buckets.setdefault(
            projection.patient_id,
            {
                "patient_id": projection.patient_id,
                "patient_name": projection.patient_name,
                "items_requiring_attention": 0,
                "critical_items": 0,
                "relevant_divergences": 0,
                "risk_score": 0,
            },
        )
        bucket["items_requiring_attention"] = int(bucket["items_requiring_attention"]) + 1
        bucket["risk_score"] = int(bucket["risk_score"]) + _projection_risk_score(
            projection.status
        )

        if projection.status == CalculationOperationalStatus.CRITICAL_STOCK:
            bucket["critical_items"] = int(bucket["critical_items"]) + 1
        if projection.divergence_status in RELEVANT_DIVERGENCE_STATUSES:
            bucket["relevant_divergences"] = int(bucket["relevant_divergences"]) + 1

    sorted_buckets = sorted(
        patient_buckets.values(),
        key=lambda bucket: (
            -int(bucket["risk_score"]),
            -int(bucket["critical_items"]),
            -int(bucket["items_requiring_attention"]),
            str(bucket["patient_name"]).lower(),
        ),
    )

    return [
        DashboardRiskPatientItem(
            patient_id=bucket["patient_id"],
            patient_name=str(bucket["patient_name"]),
            items_requiring_attention=int(bucket["items_requiring_attention"]),
            critical_items=int(bucket["critical_items"]),
            relevant_divergences=int(bucket["relevant_divergences"]),
            risk_score=int(bucket["risk_score"]),
        )
        for bucket in sorted_buckets[:5]
    ]


def get_dashboard_summary(
    db: Session,
) -> DashboardSummaryResponse:
    active_patients = db.scalar(
        select(func.count(Patient.id)).where(Patient.is_active.is_(True))
    ) or 0
    active_items = db.scalar(select(func.count(Item.id)).where(Item.is_active.is_(True))) or 0
    active_prescriptions = db.scalar(
        select(func.count(Prescription.id)).where(Prescription.is_active.is_(True))
    ) or 0
    open_alerts = db.scalar(
        select(func.count(Alert.id)).where(Alert.status == AlertStatus.OPEN)
    ) or 0

    stock_subquery = _build_stock_subquery()
    low_stock_items = db.scalar(
        select(func.count(Item.id))
        .outerjoin(stock_subquery, stock_subquery.c.item_id == Item.id)
        .where(Item.is_active.is_(True))
        .where(func.coalesce(stock_subquery.c.current_stock, 0) < Item.minimum_stock)
    ) or 0
    calculation_projections = list_projection_payloads(db)

    return DashboardSummaryResponse(
        active_patients=int(active_patients),
        active_items=int(active_items),
        active_prescriptions=int(active_prescriptions),
        open_alerts=int(open_alerts),
        low_stock_items=int(low_stock_items),
        calculation=_build_dashboard_calculation_summary(calculation_projections),
    )


def get_dashboard_overview(db: Session) -> DashboardOverviewResponse:
    stock_subquery = _build_stock_subquery()
    severity_order = build_alert_severity_order_expression()
    calculation_projections = list_projection_payloads(db)

    low_stock_rows = db.execute(
        select(
            Item.id.label("item_id"),
            Item.name.label("item_name"),
            Item.item_type,
            Unit.symbol.label("unit_symbol"),
            func.coalesce(stock_subquery.c.current_stock, 0).label("current_stock"),
            Item.minimum_stock,
        )
        .join(Unit, Unit.id == Item.unit_id)
        .outerjoin(stock_subquery, stock_subquery.c.item_id == Item.id)
        .where(Item.is_active.is_(True))
        .where(func.coalesce(stock_subquery.c.current_stock, 0) < Item.minimum_stock)
        .order_by(
            (Item.minimum_stock - func.coalesce(stock_subquery.c.current_stock, 0)).desc(),
            Item.name.asc(),
        )
        .limit(10)
    ).all()

    open_alert_rows = db.execute(
        select(
            Alert.id,
            Alert.title,
            Alert.message,
            Alert.severity,
            Alert.item_id,
            Alert.patient_id,
            Alert.created_at,
        )
        .where(Alert.status == AlertStatus.OPEN)
        .order_by(severity_order.desc(), Alert.created_at.desc())
        .limit(10)
    ).all()

    recent_movement_rows = db.execute(
        select(
            InventoryMovement.id,
            InventoryMovement.item_id,
            Item.name.label("item_name"),
            Unit.symbol.label("unit_symbol"),
            InventoryMovement.movement_type,
            InventoryMovement.adjustment_operation,
            InventoryMovement.quantity,
            InventoryMovement.patient_id,
            InventoryMovement.occurred_at,
        )
        .join(Item, Item.id == InventoryMovement.item_id)
        .join(Unit, Unit.id == InventoryMovement.unit_id)
        .order_by(InventoryMovement.occurred_at.desc(), InventoryMovement.created_at.desc())
        .limit(10)
    ).all()

    recent_movements = [
        DashboardRecentMovementItem(
            id=row.id,
            item_id=row.item_id,
            item_name=row.item_name,
            unit_symbol=row.unit_symbol,
            movement_type=row.movement_type,
            quantity=row.quantity,
            stock_effect=calculate_inventory_stock_effect(
                row.movement_type,
                row.quantity,
                row.adjustment_operation,
            ),
            patient_id=row.patient_id,
            occurred_at=row.occurred_at,
        )
        for row in recent_movement_rows
    ]

    return DashboardOverviewResponse(
        calculation=_build_dashboard_calculation_summary(calculation_projections),
        risk_patients=_build_dashboard_risk_patients(calculation_projections),
        low_stock_items=[
            DashboardLowStockItem(
                item_id=row.item_id,
                item_name=row.item_name,
                item_type=row.item_type,
                unit_symbol=row.unit_symbol,
                current_stock=row.current_stock,
                minimum_stock=row.minimum_stock,
                shortage_amount=row.minimum_stock - row.current_stock,
            )
            for row in low_stock_rows
        ],
        open_alerts=[
            DashboardOpenAlertItem(
                id=row.id,
                title=row.title,
                message=row.message,
                severity=row.severity,
                item_id=row.item_id,
                patient_id=row.patient_id,
                created_at=row.created_at,
            )
            for row in open_alert_rows
        ],
        recent_movements=recent_movements,
    )


def get_patient_details(db: Session, patient_id: UUID) -> PatientDetailsResponse:
    patient = _get_patient_or_raise(db, patient_id)

    active_prescriptions = db.scalar(
        select(func.count(Prescription.id))
        .where(Prescription.patient_id == patient_id)
        .where(Prescription.is_active.is_(True))
    ) or 0
    active_items = db.scalar(
        select(func.count(distinct(Prescription.item_id)))
        .where(Prescription.patient_id == patient_id)
        .where(Prescription.is_active.is_(True))
    ) or 0
    open_alerts_count = db.scalar(
        select(func.count(Alert.id))
        .where(Alert.patient_id == patient_id)
        .where(Alert.status == AlertStatus.OPEN)
    ) or 0

    alerts_rows = db.execute(
        select(Alert.id, Alert.title, Alert.message, Alert.severity, Alert.created_at)
        .where(Alert.patient_id == patient_id)
        .where(Alert.status == AlertStatus.OPEN)
        .order_by(Alert.created_at.desc())
        .limit(5)
    ).all()

    movement_rows = db.execute(
        select(
            InventoryMovement.id,
            InventoryMovement.item_id,
            Item.name,
            Unit.symbol,
            InventoryMovement.movement_type,
            InventoryMovement.quantity,
            InventoryMovement.occurred_at,
        )
        .join(Item, Item.id == InventoryMovement.item_id)
        .join(Unit, Unit.id == InventoryMovement.unit_id)
        .where(InventoryMovement.patient_id == patient_id)
        .order_by(InventoryMovement.occurred_at.desc(), InventoryMovement.created_at.desc())
        .limit(10)
    ).all()

    return PatientDetailsResponse(
        id=patient.id,
        full_name=patient.full_name,
        birth_date=patient.birth_date,
        care_notes=patient.care_notes,
        is_active=patient.is_active,
        metrics=PatientDetailsMetrics(
            active_prescriptions=int(active_prescriptions),
            active_items=int(active_items),
            open_alerts=int(open_alerts_count),
        ),
        open_alerts=[
            PatientDetailsAlertItem(
                id=row.id,
                title=row.title,
                message=row.message,
                severity=row.severity,
                created_at=row.created_at,
            )
            for row in alerts_rows
        ],
        recent_movements=[
            PatientDetailsMovementItem(
                id=row.id,
                item_id=row.item_id,
                item_name=row.name,
                unit_symbol=row.symbol,
                movement_type=row.movement_type,
                quantity=row.quantity,
                occurred_at=row.occurred_at,
            )
            for row in movement_rows
        ],
    )


def get_patient_active_items(db: Session, patient_id: UUID) -> list[PatientActiveItemResponse]:
    _get_patient_or_raise(db, patient_id)
    stock_subquery = _build_stock_subquery()

    rows = db.execute(
        select(
            Prescription.id.label("prescription_id"),
            Prescription.item_id,
            Prescription.dose_amount,
            Prescription.frequency_per_day,
            Prescription.specific_times,
            Prescription.usage_mode,
            Prescription.comparison_window,
            Prescription.min_expected_per_day,
            Prescription.max_expected_per_day,
            Prescription.start_date,
            Prescription.end_date,
            Item.name.label("item_name"),
            Item.item_type,
            Item.unit_id,
            Item.minimum_stock,
            Unit.symbol.label("unit_symbol"),
            func.coalesce(stock_subquery.c.current_stock, 0).label("current_stock"),
        )
        .join(Item, Item.id == Prescription.item_id)
        .join(Unit, Unit.id == Item.unit_id)
        .outerjoin(stock_subquery, stock_subquery.c.item_id == Item.id)
        .where(Prescription.patient_id == patient_id)
        .where(Prescription.is_active.is_(True))
        .order_by(Item.name.asc(), Prescription.start_date.desc())
    ).all()

    return [
        PatientActiveItemResponse(
            prescription_id=row.prescription_id,
            item_id=row.item_id,
            item_name=row.item_name,
            item_type=row.item_type,
            unit_id=row.unit_id,
            unit_symbol=row.unit_symbol,
            dose_amount=row.dose_amount,
            frequency_per_day=row.frequency_per_day,
            specific_times=row.specific_times,
            usage_mode=row.usage_mode,
            comparison_window=row.comparison_window,
            min_expected_per_day=row.min_expected_per_day,
            max_expected_per_day=row.max_expected_per_day,
            start_date=row.start_date,
            end_date=row.end_date,
            current_stock=row.current_stock,
            minimum_stock=row.minimum_stock,
            is_below_minimum=row.current_stock < row.minimum_stock,
        )
        for row in rows
    ]
