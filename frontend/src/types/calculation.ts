import type { ApiEnvelope, ApiListEnvelope } from "@/types/api"
import type {
  PrescriptionComparisonWindow,
  PrescriptionUsageMode,
} from "@/types/prescription"

export type CalculationStatus =
  | "ok"
  | "low_stock"
  | "critical_stock"
  | "consumption_above_expected"
  | "consumption_below_expected"
  | "inconsistent_data"
  | "invalid_prescription"

export type CalculationDivergenceStatus =
  | "above_expected"
  | "below_expected"
  | "coherent"
  | "not_available"

export type CalculationDoseOccurrenceState =
  | "not_due_yet"
  | "due_now"
  | "overdue"
  | "completed"

export type CalculationAdministrationDayStatus =
  | "not_due_yet"
  | "due_now"
  | "overdue"
  | "completed"
  | "partially_completed_day"
  | "missed_dose"
  | "invalid_schedule"

export type CalculationDoseOccurrence = {
  scheduled_at: string
  tolerated_until: string
  dose_amount: string
  state: CalculationDoseOccurrenceState
  prescription_id: string | null
  matched_occurred_at: string | null
}

export type CalculationDoseScheduleSummary = {
  total_doses: number
  completed_dose_count: number
  due_now_dose_count: number
  overdue_dose_count: number
  not_due_yet_dose_count: number
  next_dose: CalculationDoseOccurrence | null
  overdue_dose: CalculationDoseOccurrence | null
}

export type CalculationProjection = {
  reference_date: string
  patient_id: string
  patient_name: string | null
  item_id: string
  item_name: string
  unit_symbol: string | null
  usage_mode: PrescriptionUsageMode | null
  comparison_window: PrescriptionComparisonWindow | null
  min_expected_per_day: string | null
  max_expected_per_day: string | null
  daily_consumption: string
  current_stock: string
  days_remaining: string | null
  expected_consumption_until_now: string | null
  actual_consumption_until_now: string | null
  divergence: string | null
  divergence_status: CalculationDivergenceStatus
  dose_occurrences: CalculationDoseOccurrence[] | null
  dose_schedule: CalculationDoseScheduleSummary | null
  administration_day_status: CalculationAdministrationDayStatus | null
  administration_day_reason: string | null
  status: CalculationStatus
  should_alert: boolean
  alert_reason: string | null
  is_valid: boolean
  invalid_reason: string | null
}

export type PatientConsumptionSummary = {
  patient_id: string
  patient_name: string | null
  reference_date: string
  items: CalculationProjection[]
  total_items: number
  items_requiring_attention: number
  invalid_items: number
}

export type CalculationAvailabilitySnapshot = {
  stock_available: boolean
  predicted_consumption_available: boolean
  realized_consumption_available: boolean
  days_remaining_available: boolean
  divergence_available: boolean
  status_context_available: boolean
  alert_context_available: boolean
}

export type CalculationMetricsSnapshot = {
  current_stock: string
  minimum_stock: string
  active_prescriptions: number
  predicted_daily_consumption: string
  realized_total_administration: string
  realized_daily_average: string
  realized_window_days: number
  days_remaining: string | null
}

export type CalculationDivergenceSnapshot = {
  comparable: boolean
  quantity_gap: string | null
  percent_gap: string | null
  default_threshold_percent: string
  exceeds_default_threshold: boolean
}

export type CalculationStatusContextSnapshot = {
  below_minimum_stock: boolean
  out_of_stock: boolean
  has_prediction: boolean
  has_realized_history: boolean
  days_remaining: string | null
  divergence_detected: boolean
  ready_for_status_classification: boolean
}

export type CalculationItemProjection = {
  reference_date: string
  item_id: string
  item_name: string
  item_type: string
  unit_id: string | null
  unit_symbol: string | null
  availability: CalculationAvailabilitySnapshot
  metrics: CalculationMetricsSnapshot
  divergence: CalculationDivergenceSnapshot
  status_context: CalculationStatusContextSnapshot
}

export type DashboardCalculationSummary = {
  items_at_risk: number
  critical_items: number
  relevant_divergences: number
  patients_at_risk: number
}

export type CalculationAlertCandidate = CalculationProjection

export type PatientDoseScheduleEntry = {
  patient_id: string
  patient_name: string | null
  item_id: string
  item_name: string
  unit_symbol: string | null
  usage_mode: PrescriptionUsageMode | null
  comparison_window: PrescriptionComparisonWindow | null
  administration_day_status: CalculationAdministrationDayStatus | null
  administration_day_reason: string | null
  scheduled_at: string
  tolerated_until: string
  dose_amount: string
  state: CalculationDoseOccurrenceState
  prescription_id: string | null
  matched_occurred_at: string | null
}

export type PatientDoseSchedule = {
  patient_id: string
  patient_name: string | null
  reference_date: string
  doses: PatientDoseScheduleEntry[]
  total_doses: number
  completed_dose_count: number
  due_now_dose_count: number
  overdue_dose_count: number
  not_due_yet_dose_count: number
  next_dose: PatientDoseScheduleEntry | null
  overdue_doses: PatientDoseScheduleEntry[]
}

export type CalculationPatientItemProjectionResponse = ApiEnvelope<CalculationProjection>
export type CalculationPatientConsumptionSummaryResponse =
  ApiEnvelope<PatientConsumptionSummary>
export type CalculationItemProjectionResponse = ApiEnvelope<CalculationItemProjection>
export type CalculationAlertCandidatesResponse =
  ApiListEnvelope<CalculationAlertCandidate>
export type PatientDoseScheduleResponse = ApiEnvelope<PatientDoseSchedule>

export type CalculationAlertSyncResult = {
  candidate_total: number
  created: number
  updated: number
  resolved: number
  unchanged: number
}

export type CalculationAlertSyncResponse = ApiEnvelope<CalculationAlertSyncResult>
