from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel

from app.modules.items.models import ItemType
from app.modules.prescriptions.models import (
    PrescriptionComparisonWindow,
    PrescriptionUsageMode,
)


class CalculationAvailabilitySnapshot(BaseModel):
    stock_available: bool
    predicted_consumption_available: bool
    realized_consumption_available: bool
    days_remaining_available: bool
    divergence_available: bool
    status_context_available: bool
    alert_context_available: bool


class CalculationMetricsSnapshot(BaseModel):
    current_stock: Decimal
    minimum_stock: Decimal
    active_prescriptions: int
    predicted_daily_consumption: Decimal
    realized_total_administration: Decimal
    realized_daily_average: Decimal
    realized_window_days: int
    days_remaining: Decimal | None


class CalculationDivergenceSnapshot(BaseModel):
    comparable: bool
    quantity_gap: Decimal | None
    percent_gap: Decimal | None
    default_threshold_percent: Decimal
    exceeds_default_threshold: bool


class CalculationStatusContextSnapshot(BaseModel):
    below_minimum_stock: bool
    out_of_stock: bool
    has_prediction: bool
    has_realized_history: bool
    days_remaining: Decimal | None
    divergence_detected: bool
    ready_for_status_classification: bool


class CalculationItemPayload(BaseModel):
    reference_date: date
    item_id: UUID
    item_name: str
    item_type: ItemType
    unit_id: UUID
    unit_symbol: str
    availability: CalculationAvailabilitySnapshot
    metrics: CalculationMetricsSnapshot
    divergence: CalculationDivergenceSnapshot
    status_context: CalculationStatusContextSnapshot


class CalculationBatchPayload(BaseModel):
    reference_date: date
    realized_window_days: int
    data: list[CalculationItemPayload]
    total: int


class CalculationOperationalStatus(str, Enum):
    OK = "ok"
    LOW_STOCK = "low_stock"
    CRITICAL_STOCK = "critical_stock"
    CONSUMPTION_ABOVE_EXPECTED = "consumption_above_expected"
    CONSUMPTION_BELOW_EXPECTED = "consumption_below_expected"
    INCONSISTENT_DATA = "inconsistent_data"
    INVALID_PRESCRIPTION = "invalid_prescription"


class CalculationDivergenceStatus(str, Enum):
    ABOVE_EXPECTED = "above_expected"
    BELOW_EXPECTED = "below_expected"
    COHERENT = "coherent"
    NOT_AVAILABLE = "not_available"


class CalculationDoseOccurrenceState(str, Enum):
    NOT_DUE_YET = "not_due_yet"
    DUE_NOW = "due_now"
    OVERDUE = "overdue"
    COMPLETED = "completed"


class CalculationAdministrationDayStatus(str, Enum):
    NOT_DUE_YET = "not_due_yet"
    DUE_NOW = "due_now"
    OVERDUE = "overdue"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED_DAY = "partially_completed_day"
    MISSED_DOSE = "missed_dose"
    INVALID_SCHEDULE = "invalid_schedule"


class CalculationDoseOccurrence(BaseModel):
    scheduled_at: datetime
    tolerated_until: datetime
    dose_amount: Decimal
    state: CalculationDoseOccurrenceState
    prescription_id: UUID | None = None
    matched_occurred_at: datetime | None = None


class CalculationDoseScheduleSummary(BaseModel):
    total_doses: int
    completed_dose_count: int
    due_now_dose_count: int
    overdue_dose_count: int
    not_due_yet_dose_count: int
    next_dose: CalculationDoseOccurrence | None = None
    overdue_dose: CalculationDoseOccurrence | None = None


class CalculationEnginePayload(BaseModel):
    reference_date: date
    patient_id: UUID
    patient_name: str
    item_id: UUID
    item_name: str
    unit_symbol: str
    usage_mode: PrescriptionUsageMode | None = None
    comparison_window: PrescriptionComparisonWindow | None = None
    min_expected_per_day: Decimal | None = None
    max_expected_per_day: Decimal | None = None
    daily_consumption: Decimal
    current_stock: Decimal
    days_remaining: Decimal | None
    expected_consumption_until_now: Decimal | None
    actual_consumption_until_now: Decimal | None
    divergence: Decimal | None
    divergence_status: CalculationDivergenceStatus
    dose_occurrences: list[CalculationDoseOccurrence] | None = None
    dose_schedule: CalculationDoseScheduleSummary | None = None
    administration_day_status: CalculationAdministrationDayStatus | None = None
    administration_day_reason: str | None = None
    status: CalculationOperationalStatus
    should_alert: bool
    alert_reason: str | None
    is_valid: bool
    invalid_reason: str | None


class CalculationEngineEnvelope(BaseModel):
    data: CalculationEnginePayload


class CalculationEngineListEnvelope(BaseModel):
    data: list[CalculationEnginePayload]
    total: int


class CalculationItemProjectionEnvelope(BaseModel):
    data: CalculationItemPayload


class PatientConsumptionSummaryResponse(BaseModel):
    patient_id: UUID
    patient_name: str
    items: list[CalculationEnginePayload]
    total_items: int
    items_requiring_attention: int
    invalid_items: int


class PatientConsumptionSummaryEnvelope(BaseModel):
    data: PatientConsumptionSummaryResponse


class PatientDoseScheduleEntry(BaseModel):
    patient_id: UUID
    patient_name: str
    item_id: UUID
    item_name: str
    unit_symbol: str
    usage_mode: PrescriptionUsageMode | None = None
    comparison_window: PrescriptionComparisonWindow | None = None
    administration_day_status: CalculationAdministrationDayStatus | None = None
    administration_day_reason: str | None = None
    scheduled_at: datetime
    tolerated_until: datetime
    dose_amount: Decimal
    state: CalculationDoseOccurrenceState
    prescription_id: UUID | None = None
    matched_occurred_at: datetime | None = None


class PatientDoseScheduleResponse(BaseModel):
    patient_id: UUID
    patient_name: str
    reference_date: date
    doses: list[PatientDoseScheduleEntry]
    total_doses: int
    completed_dose_count: int
    due_now_dose_count: int
    overdue_dose_count: int
    not_due_yet_dose_count: int
    next_dose: PatientDoseScheduleEntry | None = None
    overdue_doses: list[PatientDoseScheduleEntry]


class PatientDoseScheduleEnvelope(BaseModel):
    data: PatientDoseScheduleResponse


class CalculationAlertSyncResponse(BaseModel):
    reference_date: date
    candidate_total: int
    created: int
    updated: int
    resolved: int
    unchanged: int


class CalculationAlertSyncEnvelope(BaseModel):
    data: CalculationAlertSyncResponse
