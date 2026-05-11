import { http } from "@/services/http"
import {
  getPatientConsumptionSummary as getPatientConsumptionSummaryFromCalculation,
  getPatientDoseSchedule as getPatientDoseScheduleFromCalculation,
} from "@/features/calculation/calculation-service"
import type {
  PatientCreatePayload,
  PatientActiveItemsResponse,
  PatientDetailResponse,
  PatientDetailsResponse,
  PatientDoseScheduleResponse,
  PatientListResponse,
  PatientUpdatePayload,
} from "@/types/patient"

function buildAuthHeaders(token: string, contentType = "application/json") {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": contentType,
  }
}

export function listPatients(token: string) {
  return http.get<PatientListResponse>("/patients?include_inactive=true", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function getPatient(token: string, patientId: string) {
  return http.get<PatientDetailResponse>(`/patients/${patientId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function getPatientDetails(token: string, patientId: string) {
  return http.get<PatientDetailsResponse>(`/patients/${patientId}/details`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function getPatientActiveItems(token: string, patientId: string) {
  return http.get<PatientActiveItemsResponse>(`/patients/${patientId}/active-items`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function getPatientConsumptionSummary(
  token: string,
  patientId: string,
  options?: {
    referenceDate?: string | null
  },
) {
  return getPatientConsumptionSummaryFromCalculation(
    token,
    patientId,
    options,
  )
}

export function getPatientDoseSchedule(
  token: string,
  patientId: string,
  options?: {
    referenceDate?: string | null
  },
) {
  return getPatientDoseScheduleFromCalculation(
    token,
    patientId,
    options,
  ) as Promise<PatientDoseScheduleResponse>
}

export function createPatient(token: string, payload: PatientCreatePayload) {
  return http.post<PatientDetailResponse>("/patients", JSON.stringify(payload), {
    headers: buildAuthHeaders(token),
  })
}

export function updatePatient(token: string, patientId: string, payload: PatientUpdatePayload) {
  return http.put<PatientDetailResponse>(`/patients/${patientId}`, JSON.stringify(payload), {
    headers: buildAuthHeaders(token),
  })
}
