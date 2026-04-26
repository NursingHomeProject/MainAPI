import { http } from "@/services/http"
import type {
  DashboardOverviewResponse,
  DashboardSummaryResponse,
} from "@/types/dashboard"

function buildAuthHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
  }
}

export function getDashboardSummary(token: string) {
  return http.get<DashboardSummaryResponse>("/dashboard/summary", {
    headers: buildAuthHeaders(token),
  })
}

export function getDashboardOverview(token: string) {
  return http.get<DashboardOverviewResponse>("/dashboard/overview", {
    headers: buildAuthHeaders(token),
  })
}
