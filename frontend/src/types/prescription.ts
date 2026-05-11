import type { ApiEnvelope, ApiListEnvelope } from "@/types/api"

export type PrescriptionUsageMode = "fixed" | "variable" | "on_demand"

export type PrescriptionComparisonWindow =
  | "scheduled_times"
  | "daily_total"
  | "shift_window"
  | "rolling_24h"

export type Prescription = {
  id: string
  patient_id: string
  item_id: string
  dose_amount: string
  frequency_per_day: number
  specific_times: string[] | null
  usage_mode: PrescriptionUsageMode
  comparison_window: PrescriptionComparisonWindow
  min_expected_per_day: string | null
  max_expected_per_day: string | null
  start_date: string
  end_date: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export type PrescriptionCreatePayload = {
  patient_id: string
  item_id: string
  dose_amount: string
  frequency_per_day: number
  specific_times: string[] | null
  usage_mode: PrescriptionUsageMode
  comparison_window: PrescriptionComparisonWindow
  min_expected_per_day: string | null
  max_expected_per_day: string | null
  start_date: string
  end_date: string | null
  is_active: boolean
}

export type PrescriptionUpdatePayload = Partial<PrescriptionCreatePayload>

export type PrescriptionListResponse = ApiListEnvelope<Prescription>
export type PrescriptionDetailResponse = ApiEnvelope<Prescription>
