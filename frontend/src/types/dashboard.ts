import type { ApiEnvelope } from "@/types/api"
import type { DashboardCalculationSummary } from "@/types/calculation"

export type { DashboardCalculationSummary }

export type DashboardSummary = {
  active_patients: number
  active_items: number
  active_prescriptions: number
  open_alerts: number
  low_stock_items: number
  calculation: DashboardCalculationSummary
}

export type DashboardSummaryResponse = ApiEnvelope<DashboardSummary>

export type DashboardRiskPatient = {
  patient_id: string
  patient_name: string
  items_requiring_attention: number
  critical_items: number
  relevant_divergences: number
  risk_score: number
}

export type DashboardOverview = {
  calculation: DashboardCalculationSummary
  risk_patients: DashboardRiskPatient[]
}

export type DashboardOverviewResponse = ApiEnvelope<DashboardOverview>
