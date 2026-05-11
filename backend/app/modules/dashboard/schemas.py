from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.modules.internal_alerts.models import AlertSeverity
from app.modules.inventory.models import InventoryMovementType
from app.modules.items.models import ItemType
from app.modules.prescriptions.models import (
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)


class DashboardCalculationSummary(BaseModel):
    items_at_risk: int
    critical_items: int
    relevant_divergences: int
    patients_at_risk: int


class DashboardRiskPatientItem(BaseModel):
    patient_id: UUID
    patient_name: str
    items_requiring_attention: int
    critical_items: int
    relevant_divergences: int
    risk_score: int


class DashboardSummaryResponse(BaseModel):
    active_patients: int
    active_items: int
    active_prescriptions: int
    open_alerts: int
    low_stock_items: int
    calculation: DashboardCalculationSummary


class DashboardSummaryEnvelope(BaseModel):
    data: DashboardSummaryResponse


class DashboardLowStockItem(BaseModel):
    item_id: UUID
    item_name: str
    item_type: ItemType
    unit_symbol: str
    current_stock: Decimal
    minimum_stock: Decimal
    shortage_amount: Decimal


class DashboardOpenAlertItem(BaseModel):
    id: UUID
    title: str
    message: str
    severity: AlertSeverity
    item_id: UUID | None
    patient_id: UUID | None
    created_at: datetime


class DashboardRecentMovementItem(BaseModel):
    id: UUID
    item_id: UUID
    item_name: str
    unit_symbol: str
    movement_type: InventoryMovementType
    quantity: Decimal
    stock_effect: Decimal
    patient_id: UUID | None
    occurred_at: datetime


class DashboardOverviewResponse(BaseModel):
    calculation: DashboardCalculationSummary
    risk_patients: list[DashboardRiskPatientItem]
    low_stock_items: list[DashboardLowStockItem]
    open_alerts: list[DashboardOpenAlertItem]
    recent_movements: list[DashboardRecentMovementItem]


class DashboardOverviewEnvelope(BaseModel):
    data: DashboardOverviewResponse


class PatientDetailsMetrics(BaseModel):
    active_prescriptions: int
    active_items: int
    open_alerts: int


class PatientDetailsAlertItem(BaseModel):
    id: UUID
    title: str
    message: str
    severity: AlertSeverity
    created_at: datetime


class PatientDetailsMovementItem(BaseModel):
    id: UUID
    item_id: UUID
    item_name: str
    unit_symbol: str
    movement_type: InventoryMovementType
    quantity: Decimal
    occurred_at: datetime


class PatientDetailsResponse(BaseModel):
    id: UUID
    full_name: str
    birth_date: date | None
    care_notes: str | None
    is_active: bool
    metrics: PatientDetailsMetrics
    open_alerts: list[PatientDetailsAlertItem]
    recent_movements: list[PatientDetailsMovementItem]


class PatientDetailsEnvelope(BaseModel):
    data: PatientDetailsResponse


class PatientActiveItemResponse(BaseModel):
    prescription_id: UUID
    item_id: UUID
    item_name: str
    item_type: ItemType
    unit_id: UUID
    unit_symbol: str
    dose_amount: Decimal
    frequency_per_day: int
    specific_times: list[str] | None
    usage_mode: PrescriptionUsageMode
    comparison_window: PrescriptionComparisonWindow
    min_expected_per_day: Decimal | None
    max_expected_per_day: Decimal | None
    start_date: date
    end_date: date | None
    current_stock: Decimal
    minimum_stock: Decimal
    is_below_minimum: bool


class PatientActiveItemsEnvelope(BaseModel):
    data: list[PatientActiveItemResponse]
    total: int
