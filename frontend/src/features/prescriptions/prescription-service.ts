import { http } from "@/services/http"
import type {
  PrescriptionCreatePayload,
  PrescriptionDetailResponse,
  PrescriptionListResponse,
  PrescriptionUpdatePayload,
} from "@/types/prescription"

function buildAuthHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  }
}

export function listPrescriptionsByPatient(token: string, patientId: string) {
  return http.get<PrescriptionListResponse>(`/patients/${patientId}/prescriptions?include_inactive=true`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function createPrescription(token: string, payload: PrescriptionCreatePayload) {
  return http.post<PrescriptionDetailResponse>("/prescriptions", JSON.stringify(payload), {
    headers: buildAuthHeaders(token),
  })
}

export function updatePrescription(token: string, prescriptionId: string, payload: PrescriptionUpdatePayload) {
  return http.put<PrescriptionDetailResponse>(`/prescriptions/${prescriptionId}`, JSON.stringify(payload), {
    headers: buildAuthHeaders(token),
  })
}
