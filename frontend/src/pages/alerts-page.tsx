import { useCallback, useEffect, useRef, useState } from "react"
import { AlertTriangle, BellRing, RefreshCw, ShieldCheck } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"

import { CalculationAlertCandidatesList } from "@/components/app/calculation-alert-candidates-list"
import { EmptyState } from "@/components/app/empty-state"
import { FeedbackBanner } from "@/components/app/feedback-banner"
import { NativeSelect } from "@/components/app/native-select"
import { PageHeader } from "@/components/app/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  getAlertsSummaryWithFallback,
  listAlerts,
  resolveAlert,
} from "@/features/alerts/alert-service"
import { useAuth } from "@/features/auth/use-auth"
import {
  getCalculationAlertCandidates,
  syncCalculationAlerts,
} from "@/features/calculation/calculation-service"
import { listItems } from "@/features/items/item-service"
import { listPatients } from "@/features/patients/patient-service"
import { formatOperationalTextNumbers } from "@/lib/utils"
import { HttpError } from "@/services/http"
import type { AlertSeverity, AlertStatus, AlertSummary, InternalAlert } from "@/types/alert"
import type { CalculationAlertCandidate } from "@/types/calculation"
import type { Item } from "@/types/item"
import type { Patient } from "@/types/patient"

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível concluir a operação com os alertas."
}

function getSeverityBadgeVariant(severity: AlertSeverity) {
  switch (severity) {
    case "critical":
      return "danger" as const
    case "warning":
      return "warning" as const
    case "info":
      return "outline" as const
  }
}

function getSeverityLabel(severity: AlertSeverity) {
  switch (severity) {
    case "critical":
      return "Crítico"
    case "warning":
      return "Aviso"
    case "info":
      return "Informativo"
  }
}

function getStatusBadgeVariant(status: AlertStatus) {
  return status === "open" ? "warning" : "success"
}

function getStatusLabel(status: AlertStatus) {
  return status === "open" ? "Aberto" : "Resolvido"
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
}

type AlertOverviewCardProps = {
  description?: string
  onClick: () => void
  title: string
  value: number | string
}

function AlertOverviewCard({ description, onClick, title, value }: AlertOverviewCardProps) {
  return (
    <button
      className="text-left transition-transform hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      onClick={onClick}
      type="button"
    >
      <Card className="bg-white/92 hover:border-primary/40 hover:bg-white">
        <CardContent className="p-5">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="mt-2 text-3xl font-semibold">{value}</p>
          {description ? <p className="mt-3 text-xs text-muted-foreground">{description}</p> : null}
        </CardContent>
      </Card>
    </button>
  )
}

export function AlertsPage() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [alerts, setAlerts] = useState<InternalAlert[]>([])
  const [candidates, setCandidates] = useState<CalculationAlertCandidate[]>([])
  const [summary, setSummary] = useState<AlertSummary | null>(null)
  const [patients, setPatients] = useState<Patient[]>([])
  const [items, setItems] = useState<Item[]>([])
  const [statusFilter, setStatusFilter] = useState<AlertStatus | "">("")
  const [severityFilter, setSeverityFilter] = useState<AlertSeverity | "">("")
  const [patientFilter, setPatientFilter] = useState<string>("")
  const [itemFilter, setItemFilter] = useState<string>("")
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [resolvingAlertId, setResolvingAlertId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const filtersRef = useRef<HTMLDivElement | null>(null)
  const candidatesRef = useRef<HTMLDivElement | null>(null)

  const patientNameById = new Map(patients.map((patient) => [patient.id, patient.full_name]))
  const itemNameById = new Map(items.map((item) => [item.id, item.name]))

  const openAlerts = summary?.open_total ?? 0
  const candidatesRequiringAttention = candidates.filter(
    (candidate) => candidate.should_alert,
  ).length

  function scrollToFilters() {
    filtersRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  function scrollToCandidates() {
    candidatesRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  function applyAlertFilters(options?: {
    severity?: AlertSeverity | ""
    status?: AlertStatus | ""
  }) {
    setStatusFilter(options?.status ?? "")
    setSeverityFilter(options?.severity ?? "")
    setPatientFilter("")
    setItemFilter("")
    window.setTimeout(scrollToFilters, 50)
  }

  const loadAlerts = useCallback(async (showLoading = true) => {
    if (!token) {
      setAlerts([])
      setSummary(null)
      setError("Não foi possível identificar a sessão atual.")
      setIsLoading(false)
      return
    }

    if (showLoading) {
      setIsLoading(true)
    }
    setError(null)

    try {
      let syncWarning: string | null = null
      const filters = {
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        patient_id: patientFilter || undefined,
        item_id: itemFilter || undefined,
      }

      try {
        await syncCalculationAlerts(token)
      } catch {
        syncWarning =
          "Não foi possível atualizar os alertas automáticos agora. Exibindo os dados mais recentes disponiveis."
      }

      const [alertsResponse, summaryResponse, candidatesResponse] = await Promise.all([
        listAlerts(token, {
          ...filters,
        }),
        getAlertsSummaryWithFallback(token),
        getCalculationAlertCandidates(token, { limit: 20 }),
      ])
      setAlerts(alertsResponse.data)
      setSummary(summaryResponse.data)
      setCandidates(candidatesResponse.data)
      if (syncWarning) {
        setError(syncWarning)
      }
    } catch (requestError) {
      setAlerts([])
      setSummary(null)
      setCandidates([])
      setError(getErrorMessage(requestError))
    } finally {
      if (showLoading) {
        setIsLoading(false)
      }
    }
  }, [itemFilter, patientFilter, severityFilter, statusFilter, token])

  useEffect(() => {
    void loadAlerts()
  }, [loadAlerts])

  useEffect(() => {
    async function loadReferenceData() {
      if (!token) {
        setPatients([])
        setItems([])
        return
      }

      try {
        const [patientsResponse, itemsResponse] = await Promise.all([
          listPatients(token),
          listItems(token),
        ])
        setPatients(patientsResponse.data)
        setItems(itemsResponse.data)
      } catch {
        setPatients([])
        setItems([])
      }
    }

    void loadReferenceData()
  }, [token])

  async function handleResolve(alertId: string) {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      return
    }

    setResolvingAlertId(alertId)
    setError(null)
    setSuccessMessage(null)

    try {
      const response = await resolveAlert(token, alertId)
      await loadAlerts(false)
      setSuccessMessage(response.message)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setResolvingAlertId(null)
    }
  }

  return (
    <div className="grid gap-6">
      <PageHeader
        actions={
          <Button onClick={() => void loadAlerts()} variant="outline">
            <RefreshCw className="h-4 w-4" />
            Atualizar alertas
          </Button>
        }
        description="Acompanhe os alertas registrados e os sinais identificados pelo motor de cálculo."
        title="Alertas internos"
      />

      <section className="grid gap-4 md:grid-cols-4">
        <AlertOverviewCard
          description="Abrir a lista de alertas pendentes."
          onClick={() => applyAlertFilters({ status: "open" })}
          title="Alertas abertos"
          value={isLoading ? "..." : openAlerts}
        />
        <AlertOverviewCard
          description="Mostrar apenas alertas críticos ainda abertos."
          onClick={() => applyAlertFilters({ severity: "critical", status: "open" })}
          title="Alertas críticos abertos"
          value={isLoading ? "..." : summary?.open_critical ?? 0}
        />
        <AlertOverviewCard
          description="Mostrar alertas já resolvidos."
          onClick={() => applyAlertFilters({ status: "resolved" })}
          title="Alertas resolvidos"
          value={isLoading ? "..." : summary?.resolved_total ?? 0}
        />
        <AlertOverviewCard
          description="Ir direto para os casos identificados pelo motor."
          onClick={scrollToCandidates}
          title="Candidatos do motor"
          value={isLoading ? "..." : candidatesRequiringAttention}
        />
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <AlertOverviewCard
          description="Mostrar alertas de aviso em aberto."
          onClick={() => applyAlertFilters({ severity: "warning", status: "open" })}
          title="Alertas de aviso"
          value={isLoading ? "..." : summary?.open_warning ?? 0}
        />
        <AlertOverviewCard
          description="Abrir a lista de pacientes para acompanhar os casos sinalizados."
          onClick={() => navigate("/patients")}
          title="Pacientes com alerta aberto"
          value={isLoading ? "..." : summary?.patients_with_open_alerts ?? 0}
        />
        <AlertOverviewCard
          description="Abrir a lista de itens para consultar a situação operacional."
          onClick={() => navigate("/items")}
          title="Itens com alerta aberto"
          value={isLoading ? "..." : summary?.items_with_open_alerts ?? 0}
        />
      </section>

      <div ref={filtersRef}>
        <Card className="bg-white/92">
          <CardHeader>
            <CardTitle>Filtros</CardTitle>
            <CardDescription>Use os filtros para encontrar os alertas que precisam de atenção.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="alerts-status-filter">
                Status
              </label>
              <NativeSelect
                id="alerts-status-filter"
                onChange={(event) => setStatusFilter((event.target.value as AlertStatus | "") || "")}
                value={statusFilter}
              >
                <option value="">Todos os status</option>
                <option value="open">Abertos</option>
                <option value="resolved">Resolvidos</option>
              </NativeSelect>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="alerts-severity-filter">
                Severidade
              </label>
              <NativeSelect
                id="alerts-severity-filter"
                onChange={(event) => setSeverityFilter((event.target.value as AlertSeverity | "") || "")}
                value={severityFilter}
              >
                <option value="">Todas as severidades</option>
                <option value="critical">Crítico</option>
                <option value="warning">Aviso</option>
                <option value="info">Informativo</option>
              </NativeSelect>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="alerts-patient-filter">
                Paciente
              </label>
              <NativeSelect
                id="alerts-patient-filter"
                onChange={(event) => setPatientFilter(event.target.value)}
                value={patientFilter}
              >
                <option value="">Todos os pacientes</option>
                {patients.map((patient) => (
                  <option key={patient.id} value={patient.id}>
                    {patient.full_name}
                  </option>
                ))}
              </NativeSelect>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="alerts-item-filter">
                Item
              </label>
              <NativeSelect
                id="alerts-item-filter"
                onChange={(event) => setItemFilter(event.target.value)}
                value={itemFilter}
              >
                <option value="">Todos os itens</option>
                {items.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </NativeSelect>
            </div>
          </CardContent>
        </Card>
      </div>

      {successMessage ? <FeedbackBanner message={successMessage} variant="success" /> : null}

      {error ? <FeedbackBanner message={error} variant="error" /> : null}

      <div ref={candidatesRef}>
        <CalculationAlertCandidatesList candidates={candidates} isLoading={isLoading} />
      </div>

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

      {!isLoading && alerts.length === 0 ? (
        <Card className="bg-white/92">
          <CardContent>
            <EmptyState
              description="Ajuste os filtros para localizar alertas específicos ou aguarde novos registros."
              icon={BellRing}
              title="Nenhum alerta encontrado"
            />
          </CardContent>
        </Card>
      ) : null}

      {!isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {alerts.map((alert) => (
            <Card className="bg-white/92" key={alert.id}>
              <CardHeader className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-primary" />
                      {alert.title}
                    </CardTitle>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant={getSeverityBadgeVariant(alert.severity)}>{getSeverityLabel(alert.severity)}</Badge>
                    <Badge variant={getStatusBadgeVariant(alert.status)}>{getStatusLabel(alert.status)}</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                  <p className="text-muted-foreground">Motivo principal</p>
                  <p className="mt-2 font-medium text-foreground">
                    {formatOperationalTextNumbers(alert.reason || alert.message)}
                  </p>
                </div>

                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                  <p className="text-muted-foreground">Mensagem</p>
                  <p className="mt-2 font-medium text-foreground">
                    {formatOperationalTextNumbers(alert.message)}
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-border/70 bg-secondary/20 p-4">
                    <p className="text-muted-foreground">Paciente</p>
                    <p className="mt-2 font-medium">
                      {alert.patient_id
                        ? patientNameById.get(alert.patient_id) ?? alert.patient_id
                        : "Não vinculado"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-secondary/20 p-4">
                    <p className="text-muted-foreground">Item</p>
                    <p className="mt-2 font-medium">
                      {alert.item_id ? itemNameById.get(alert.item_id) ?? alert.item_id : "Não vinculado"}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {alert.patient_id ? (
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/patients/${alert.patient_id}`}>Ver paciente</Link>
                    </Button>
                  ) : null}
                  {alert.item_id ? (
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/items/${alert.item_id}`}>Ver item</Link>
                    </Button>
                  ) : null}
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <p className="text-muted-foreground">Criado em</p>
                    <p className="mt-1 font-medium">{formatDateTime(alert.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Atualizado em</p>
                    <p className="mt-1 font-medium">{formatDateTime(alert.updated_at)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Resolvido em</p>
                    <p className="mt-1 font-medium">{alert.resolved_at ? formatDateTime(alert.resolved_at) : "Pendente"}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Resolvido por</p>
                    <p className="mt-1 font-medium">{alert.resolved_by_user_id ?? "Não informado"}</p>
                  </div>
                </div>

                <div className="flex justify-end">
                  {alert.status === "open" ? (
                    <Button
                      disabled={resolvingAlertId === alert.id}
                      onClick={() => void handleResolve(alert.id)}
                      size="sm"
                    >
                      <ShieldCheck className="h-4 w-4" />
                      {resolvingAlertId === alert.id ? "Resolvendo..." : "Resolver alerta"}
                    </Button>
                  ) : (
                    <Badge variant="success">Resolvido</Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  )
}
