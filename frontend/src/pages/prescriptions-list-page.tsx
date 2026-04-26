import { useCallback, useEffect, useMemo, useState } from "react"
import { ClipboardList, Plus, RefreshCw, SquarePen } from "lucide-react"
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom"

import { EmptyState } from "@/components/app/empty-state"
import { FeedbackBanner } from "@/components/app/feedback-banner"
import { NativeSelect } from "@/components/app/native-select"
import { PageHeader } from "@/components/app/page-header"
import { CalculationStatusBadge } from "@/components/app/calculation-status-badge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/features/auth/use-auth"
import { listItems } from "@/features/items/item-service"
import { getPatientConsumptionSummary, listPatients } from "@/features/patients/patient-service"
import {
  formatExpectedRange,
  getComparisonWindowLabel,
  getUsageModeLabel,
} from "@/features/prescriptions/prescription-presentation"
import { listPrescriptionsByPatient } from "@/features/prescriptions/prescription-service"
import { formatDecimalAsInteger } from "@/lib/utils"
import { HttpError } from "@/services/http"
import type { Item } from "@/types/item"
import type { Patient, PatientConsumptionSummary } from "@/types/patient"
import type { Prescription } from "@/types/prescription"

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível carregar as prescrições."
}

function formatProjectionMetric(value: string | null, unitSymbol?: string | null) {
  if (!value) {
    return "Não disponível"
  }

  const formattedValue = formatDecimalAsInteger(value)
  return unitSymbol ? `${formattedValue} ${unitSymbol}` : formattedValue
}

function formatDaysRemaining(value: string | null) {
  if (!value) {
    return "Não disponível"
  }

  return `${formatDecimalAsInteger(value)} dias`
}

export function PrescriptionsListPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { token } = useAuth()

  const [patients, setPatients] = useState<Patient[]>([])
  const [items, setItems] = useState<Item[]>([])
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([])
  const [consumptionSummary, setConsumptionSummary] = useState<PatientConsumptionSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [consumptionError, setConsumptionError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const selectedPatientId = searchParams.get("patientId") ?? ""
  const flashState = location.state as { message?: string; tone?: "success" | "error" } | null

  const selectedPatient = useMemo(
    () => patients.find((patient) => patient.id === selectedPatientId) ?? null,
    [patients, selectedPatientId],
  )
  const itemMap = useMemo(() => new Map(items.map((item) => [item.id, item])), [items])
  const projectionByItemId = useMemo(
    () =>
      new Map(
        consumptionSummary?.items.map((projection) => [projection.item_id, projection]) ?? [],
      ),
    [consumptionSummary],
  )

  const loadPrescriptions = useCallback(async () => {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      setPatients([])
      setItems([])
      setPrescriptions([])
      setConsumptionSummary(null)
      setConsumptionError(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const [patientsResponse, itemsResponse] = await Promise.all([listPatients(token), listItems(token)])
      setPatients(patientsResponse.data)
      setItems(itemsResponse.data)

      if (selectedPatientId) {
        const [prescriptionsResult, consumptionResult] = await Promise.allSettled([
          listPrescriptionsByPatient(token, selectedPatientId),
          getPatientConsumptionSummary(token, selectedPatientId),
        ])

        if (prescriptionsResult.status !== "fulfilled") {
          throw prescriptionsResult.reason
        }

        setPrescriptions(prescriptionsResult.value.data)

        if (consumptionResult.status === "fulfilled") {
          setConsumptionSummary(consumptionResult.value.data)
          setConsumptionError(null)
        } else {
          setConsumptionSummary(null)
          setConsumptionError(getErrorMessage(consumptionResult.reason))
        }
      } else {
        setPrescriptions([])
        setConsumptionSummary(null)
        setConsumptionError(null)
      }
    } catch (requestError) {
      setPatients([])
      setItems([])
      setPrescriptions([])
      setConsumptionSummary(null)
      setConsumptionError(null)
      setError(getErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [selectedPatientId, token])

  useEffect(() => {
    void loadPrescriptions()
  }, [loadPrescriptions])

  useEffect(() => {
    if (!flashState?.message) {
      return
    }

    navigate(`${location.pathname}${location.search}`, { replace: true })
  }, [flashState?.message, location.pathname, location.search, navigate])

  function handlePatientChange(patientId: string) {
    if (!patientId) {
      setSearchParams({})
      return
    }

    setSearchParams({ patientId })
  }

  return (
    <div className="grid gap-6">
      <PageHeader
        actions={
          <>
            <Button onClick={() => void loadPrescriptions()} variant="outline">
              <RefreshCw className="h-4 w-4" />
              Atualizar
            </Button>
            <Button asChild disabled={!selectedPatientId}>
              <Link to={selectedPatientId ? `/prescriptions/new?patientId=${selectedPatientId}` : "/prescriptions/new"}>
                <Plus className="h-4 w-4" />
                Nova prescrição
              </Link>
            </Button>
          </>
        }
        description="Acompanhe as prescrições de cada paciente e mantenha os tratamentos organizados."
        title="Prescrições"
      />

      <Card className="bg-white/92">
        <CardHeader>
          <CardTitle>Selecionar contexto do paciente</CardTitle>
          <CardDescription>
            Escolha um paciente para visualizar e organizar suas prescrições.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="patient-filter">
              Paciente
            </label>
            <NativeSelect
              id="patient-filter"
              onChange={(event) => handlePatientChange(event.target.value)}
              value={selectedPatientId}
            >
              <option value="">Selecione um paciente para listar prescrições</option>
              {patients.map((patient) => (
                <option key={patient.id} value={patient.id}>
                  {patient.full_name}
                  {patient.is_active ? "" : " - inativo"}
                </option>
              ))}
            </NativeSelect>
          </div>
          {selectedPatient ? (
            <div className="rounded-2xl border border-border/70 bg-secondary/20 px-4 py-3 text-sm text-muted-foreground">
              Exibindo prescrições do paciente <span className="font-medium text-foreground">{selectedPatient.full_name}</span>.
            </div>
          ) : (
            <div className="rounded-2xl border border-border/70 bg-secondary/20 px-4 py-3 text-sm text-muted-foreground">
              Escolha um paciente para visualizar suas prescrições.
            </div>
          )}
        </CardContent>
      </Card>

      {error ? <FeedbackBanner message={error} variant="error" /> : null}
      {consumptionError && selectedPatientId ? (
        <FeedbackBanner
          message={consumptionError}
          title="Não foi possível carregar a duracao estimada das prescrições"
          variant="warning"
        />
      ) : null}

      {flashState?.message ? (
        <FeedbackBanner message={flashState.message} variant={flashState.tone === "success" ? "success" : "error"} />
      ) : null}

      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 2 }).map((_, index) => (
            <Card className="bg-white/92" key={index}>
              <CardHeader>
                <div className="h-5 w-40 animate-pulse rounded bg-secondary" />
                <div className="h-4 w-52 animate-pulse rounded bg-secondary" />
              </CardHeader>
              <CardContent className="grid gap-3">
                <div className="h-4 w-full animate-pulse rounded bg-secondary" />
                <div className="h-4 w-4/5 animate-pulse rounded bg-secondary" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      {!isLoading && !selectedPatientId ? (
        <Card className="bg-white/92">
          <CardContent>
            <EmptyState
              description="Escolha um paciente para iniciar a listagem, criacao ou edição de prescrições."
              icon={ClipboardList}
              title="Selecione um paciente"
            />
          </CardContent>
        </Card>
      ) : null}

      {!isLoading && selectedPatientId && prescriptions.length === 0 ? (
        <Card className="bg-white/92">
          <CardContent>
            <EmptyState
              action={
                <Button asChild>
                  <Link to={`/prescriptions/new?patientId=${selectedPatientId}`}>Criar primeira prescrição</Link>
                </Button>
              }
              description="Este paciente ainda não possui prescrições cadastradas."
              icon={ClipboardList}
              title="Nenhuma prescrição encontrada"
            />
          </CardContent>
        </Card>
      ) : null}

      {!isLoading && selectedPatientId ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {prescriptions.map((prescription) => {
            const item = itemMap.get(prescription.item_id)
            const projection = projectionByItemId.get(prescription.item_id)

            return (
              <Card className="bg-white/92" key={prescription.id}>
                <CardHeader className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle>{item?.name ?? prescription.item_id}</CardTitle>
                      <CardDescription>
                        Dose {formatDecimalAsInteger(prescription.dose_amount)} | {prescription.frequency_per_day}x ao dia
                      </CardDescription>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {projection ? <CalculationStatusBadge status={projection.status} /> : null}
                      <Badge variant={prescription.is_active ? "success" : "outline"}>
                        {prescription.is_active ? "Ativa" : "Inativa"}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid gap-3 rounded-xl border border-border/70 bg-secondary/25 px-4 py-3 text-sm md:grid-cols-2">
                      <div>
                        <p className="text-muted-foreground">Período</p>
                      <p className="font-medium text-foreground">
                        {prescription.start_date} {prescription.end_date ? `até ${prescription.end_date}` : "sem data final"}
                      </p>
                    </div>
                      <div>
                        <p className="text-muted-foreground">Horarios específicos</p>
                        <p className="font-medium text-foreground">
                          {prescription.specific_times?.join(", ") || "Não informados"}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Tipo de uso</p>
                        <p className="font-medium text-foreground">
                          {getUsageModeLabel(prescription.usage_mode)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Lógica de comparação</p>
                        <p className="font-medium text-foreground">
                          {getComparisonWindowLabel(prescription.comparison_window)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Duracao estimada</p>
                        <p className="font-medium text-foreground">
                        {formatDaysRemaining(projection?.days_remaining ?? null)}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Consumo diario previsto</p>
                        <p className="font-medium text-foreground">
                          {formatProjectionMetric(
                            projection?.daily_consumption ?? null,
                            projection?.unit_symbol ?? null,
                          )}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Faixa esperada</p>
                        <p className="font-medium text-foreground">
                          {formatExpectedRange(
                            prescription.min_expected_per_day,
                            prescription.max_expected_per_day,
                          )}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Acompanhamento</p>
                        <p className="font-medium text-foreground">
                        {projection?.alert_reason || "Sem observações adicionais."}
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Button asChild size="sm">
                      <Link to={`/prescriptions/${prescription.id}/edit?patientId=${prescription.patient_id}`}>
                        <SquarePen className="h-4 w-4" />
                        Editar
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
