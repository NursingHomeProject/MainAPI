import type { ApiEnvelope } from "@/types/api"

export type AlertSeverity = "info" | "warning" | "critical"
export type AlertStatus = "open" | "resolved"
export type AlertSource = "manual" | "calculation_engine"

export type InternalAlert = {
  id: string
  item_id: string | null
  patient_id: string | null
  resolved_by_user_id: string | null
  alert_type: string
  title: string
  reason: string
  message: string
  severity: AlertSeverity
  status: AlertStatus
  resolved_at: string | null
  created_at: string
  updated_at: string
  is_calculation_generated: boolean
  source: AlertSource
  source_enum: AlertSource
}

export type AlertListFilters = {
  severity?: AlertSeverity
  status?: AlertStatus
  patient_id?: string
  item_id?: string
  alert_type?: string
}

export type AlertSummary = {
  open_total: number
  resolved_total: number
  open_critical: number
  open_warning: number
  open_info: number
  calculation_open: number
  manual_open: number
  patients_with_open_alerts: number
  items_with_open_alerts: number
}

export type AlertListResponse = {
  data: InternalAlert[]
  total: number
  summary: AlertSummary
}
export type AlertDetailResponse = ApiEnvelope<InternalAlert>
export type AlertSummaryResponse = ApiEnvelope<AlertSummary>
export type AlertResolveResponse = {
  message: string
  action: string | null
  already_resolved: boolean
  data: InternalAlert
}
