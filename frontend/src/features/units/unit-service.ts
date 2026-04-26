import { http } from "@/services/http"
import type { UnitCreatePayload, UnitDetailResponse, UnitListResponse, UnitUpdatePayload } from "@/types/unit"

function buildAuthHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  }
}

export function listUnits(token: string) {
  return http.get<UnitListResponse>("/units?include_inactive=true", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function getUnit(token: string, unitId: string) {
  return http.get<UnitDetailResponse>(`/units/${unitId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function createUnit(token: string, payload: UnitCreatePayload) {
  return http.post<UnitDetailResponse>("/units", JSON.stringify(payload), {
    headers: buildAuthHeaders(token),
  })
}

export function updateUnit(token: string, unitId: string, payload: UnitUpdatePayload) {
  return http.put<UnitDetailResponse>(`/units/${unitId}`, JSON.stringify(payload), {
    headers: buildAuthHeaders(token),
  })
}
