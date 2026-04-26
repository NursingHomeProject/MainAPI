import { http } from "@/services/http"
import type {
  CalculationAlertCandidatesResponse,
  CalculationAlertCandidate,
  CalculationAlertSyncResponse,
  CalculationItemProjectionResponse,
  CalculationPatientConsumptionSummaryResponse,
  CalculationPatientItemProjectionResponse,
  PatientDoseScheduleResponse,
} from "@/types/calculation"

function buildAuthHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
  }
}

function buildQueryString(
  params: Record<string, string | number | null | undefined>,
) {
  const searchParams = new URLSearchParams()

  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") {
      continue
    }

    searchParams.set(key, String(value))
  }

  const query = searchParams.toString()
  return query ? `?${query}` : ""
}

function isRelevantDivergenceCandidate(candidate: CalculationAlertCandidate) {
  return (
    candidate.divergence_status === "above_expected" ||
    candidate.divergence_status === "below_expected"
  )
}

function filterCandidatesByItem(
  candidates: CalculationAlertCandidate[],
  itemId: string,
) {
  return candidates.filter((candidate) => candidate.item_id === itemId)
}

export function getPatientItemProjection(
  token: string,
  patientId: string,
  itemId: string,
  options?: {
    referenceDate?: string | null
  },
) {
  const query = buildQueryString({
    reference_date: options?.referenceDate,
  })

  return http.get<CalculationPatientItemProjectionResponse>(
    `/patients/${patientId}/items/${itemId}/projection${query}`,
    {
      headers: buildAuthHeaders(token),
    },
  )
}

export function getPatientConsumptionSummary(
  token: string,
  patientId: string,
  options?: {
    referenceDate?: string | null
  },
) {
  const query = buildQueryString({
    reference_date: options?.referenceDate,
  })

  return http.get<CalculationPatientConsumptionSummaryResponse>(
    `/patients/${patientId}/consumption-summary${query}`,
    {
      headers: buildAuthHeaders(token),
    },
  )
}

export function getPatientDoseSchedule(
  token: string,
  patientId: string,
  options?: {
    referenceDate?: string | null
  },
) {
  const query = buildQueryString({
    reference_date: options?.referenceDate,
  })

  return http.get<PatientDoseScheduleResponse>(
    `/patients/${patientId}/dose-schedule${query}`,
    {
      headers: buildAuthHeaders(token),
    },
  )
}

export function getItemProjection(
  token: string,
  itemId: string,
  options?: {
    referenceDate?: string | null
    windowDays?: number | null
  },
) {
  const query = buildQueryString({
    reference_date: options?.referenceDate,
    window_days: options?.windowDays,
  })

  return http.get<CalculationItemProjectionResponse>(`/items/${itemId}/projection${query}`, {
    headers: buildAuthHeaders(token),
  })
}

export function getCalculationAlertCandidates(
  token: string,
  options?: {
    referenceDate?: string | null
    limit?: number | null
  },
) {
  const query = buildQueryString({
    reference_date: options?.referenceDate,
    limit: options?.limit,
  })

  return http.get<CalculationAlertCandidatesResponse>(
    `/calculations/alerts-candidates${query}`,
    {
      headers: buildAuthHeaders(token),
    },
  )
}

export async function getRelevantDivergenceCandidates(
  token: string,
  options?: {
    referenceDate?: string | null
    limit?: number | null
  },
) {
  const response = await getCalculationAlertCandidates(token, options)

  const data = response.data.filter(isRelevantDivergenceCandidate)

  return {
    ...response,
    data,
    total: data.length,
  }
}

export async function getItemAlertCandidates(
  token: string,
  itemId: string,
  options?: {
    referenceDate?: string | null
    limit?: number | null
  },
) {
  const response = await getCalculationAlertCandidates(token, options)
  const data = filterCandidatesByItem(response.data, itemId)

  return {
    ...response,
    data,
    total: data.length,
  }
}

export function syncCalculationAlerts(
  token: string,
  options?: {
    referenceDate?: string | null
  },
) {
  const query = buildQueryString({
    reference_date: options?.referenceDate,
  })

  return http.post<CalculationAlertSyncResponse>(`/calculations/alerts-sync${query}`, undefined, {
    headers: buildAuthHeaders(token),
  })
}
