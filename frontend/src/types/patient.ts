import type { ApiEnvelope, ApiListEnvelope } from "@/types/api"
import type {
  CalculationDivergenceStatus,
  PatientDoseSchedule as CalculationPatientDoseSchedule,
  PatientDoseScheduleResponse as CalculationPatientDoseScheduleResponse,
  CalculationProjection,
  CalculationStatus,
  CalculationPatientConsumptionSummaryResponse,
  PatientConsumptionSummary as CalculationPatientConsumptionSummary,
} from "@/types/calculation"
import type {
  PrescriptionComparisonWindow,
  PrescriptionUsageMode,
} from "@/types/prescription"

export type Patient = {
  id: string
  full_name: string
  birth_date: string | null
  care_notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export type PatientCreatePayload = {
  full_name: string
  birth_date: string | null
  care_notes: string | null
  is_active: boolean
}

export type PatientUpdatePayload = Partial<PatientCreatePayload>

export type PatientListResponse = ApiListEnvelope<Patient>
export type PatientDetailResponse = ApiEnvelope<Patient>

export type PatientDetailsMetrics = {
  active_prescriptions: number
  active_items: number
  open_alerts: number
}

export type PatientDetailsAlert = {
  id: string
  title: string
  message: string
  severity: string
  created_at: string
}

export type PatientDetailsMovement = {
  id: string
  item_id: string
  item_name: string
  unit_symbol: string
  movement_type: string
  quantity: string
  occurred_at: string
}

export type PatientDetails = {
  id: string
  full_name: string
  birth_date: string | null
  care_notes: string | null
  is_active: boolean
  metrics: PatientDetailsMetrics
  open_alerts: PatientDetailsAlert[]
  recent_movements: PatientDetailsMovement[]
}

export type PatientDetailsResponse = ApiEnvelope<PatientDetails>

export type PatientActiveItem = {
  prescription_id: string
  item_id: string
  item_name: string
  item_type: "medication" | "supply"
  unit_id: string
  unit_symbol: string
  dose_amount: string
  frequency_per_day: number
  specific_times: string[] | null
  usage_mode: PrescriptionUsageMode
  comparison_window: PrescriptionComparisonWindow
  min_expected_per_day: string | null
  max_expected_per_day: string | null
  start_date: string
  end_date: string | null
  current_stock: string
  minimum_stock: string
  is_below_minimum: boolean
}

export type PatientActiveItemsResponse = ApiListEnvelope<PatientActiveItem>

export type PatientCalculationStatus = CalculationStatus

export type PatientCalculationDivergenceStatus = CalculationDivergenceStatus

export type PatientConsumptionProjection = CalculationProjection

export type PatientConsumptionSummary = CalculationPatientConsumptionSummary

export type PatientConsumptionSummaryResponse =
  CalculationPatientConsumptionSummaryResponse

export type PatientDoseSchedule = CalculationPatientDoseSchedule

export type PatientDoseScheduleResponse =
  CalculationPatientDoseScheduleResponse
