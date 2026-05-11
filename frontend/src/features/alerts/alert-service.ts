import { http } from "@/services/http"
import type {
  AlertListFilters,
  AlertListResponse,
  AlertResolveResponse,
  AlertSummary,
  AlertSummaryResponse,
  InternalAlert,
} from "@/types/alert"

function buildAuthHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  }
}

function buildAlertsQuery(filters: AlertListFilters = {}) {
  const searchParams = new URLSearchParams()

  if (filters.status) {
    searchParams.set("status", filters.status)
  }

  if (filters.severity) {
    searchParams.set("severity", filters.severity)
  }

  if (filters.patient_id) {
    searchParams.set("patient_id", filters.patient_id)
  }

  if (filters.item_id) {
    searchParams.set("item_id", filters.item_id)
  }

  if (filters.alert_type) {
    searchParams.set("alert_type", filters.alert_type)
  }

  const queryString = searchParams.toString()
  return queryString ? `/alerts?${queryString}` : "/alerts"
}

export function listAlerts(token: string, filters: AlertListFilters = {}) {
  return http.get<AlertListResponse>(buildAlertsQuery(filters), {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function getAlertsSummary(token: string, filters: AlertListFilters = {}) {
  const searchParams = new URLSearchParams()

  if (filters.status) {
    searchParams.set("status", filters.status)
  }

  if (filters.severity) {
    searchParams.set("severity", filters.severity)
  }

  if (filters.patient_id) {
    searchParams.set("patient_id", filters.patient_id)
  }

  if (filters.item_id) {
    searchParams.set("item_id", filters.item_id)
  }

  if (filters.alert_type) {
    searchParams.set("alert_type", filters.alert_type)
  }

  const queryString = searchParams.toString()
  const path = queryString ? `/alerts/summary?${queryString}` : "/alerts/summary"

  return http.get<AlertSummaryResponse>(path, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function buildAlertSummaryFromAlerts(alerts: InternalAlert[]): AlertSummary {
  const patientsWithOpenAlerts = new Set<string>()
  const itemsWithOpenAlerts = new Set<string>()

  let openTotal = 0
  let resolvedTotal = 0
  let openCritical = 0
  let openWarning = 0
  let openInfo = 0
  let calculationOpen = 0
  let manualOpen = 0

  for (const alert of alerts) {
    if (alert.status === "open") {
      openTotal += 1

      if (alert.alert_type === "calculation_projection") {
        calculationOpen += 1
      } else {
        manualOpen += 1
      }

      if (alert.patient_id) {
        patientsWithOpenAlerts.add(alert.patient_id)
      }

      if (alert.item_id) {
        itemsWithOpenAlerts.add(alert.item_id)
      }

      if (alert.severity === "critical") {
        openCritical += 1
      } else if (alert.severity === "warning") {
        openWarning += 1
      } else {
        openInfo += 1
      }
    } else {
      resolvedTotal += 1
    }
  }

  return {
    open_total: openTotal,
    resolved_total: resolvedTotal,
    open_critical: openCritical,
    open_warning: openWarning,
    open_info: openInfo,
    calculation_open: calculationOpen,
    manual_open: manualOpen,
    patients_with_open_alerts: patientsWithOpenAlerts.size,
    items_with_open_alerts: itemsWithOpenAlerts.size,
  }
}

export async function getAlertsSummaryWithFallback(
  token: string,
  filters: AlertListFilters = {},
) {
  try {
    return await getAlertsSummary(token, filters)
  } catch {
    const alertsResponse = await listAlerts(token, filters)

    return {
      data: alertsResponse.summary ?? buildAlertSummaryFromAlerts(alertsResponse.data),
    } satisfies AlertSummaryResponse
  }
}

export function resolveAlert(token: string, alertId: string) {
  return http.post<AlertResolveResponse>(`/alerts/${alertId}/resolve`, null, {
    headers: buildAuthHeaders(token),
  })
}
