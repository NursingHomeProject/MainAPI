import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Activity,
  ArrowLeft,
  Bell,
  ClipboardList,
  Clock3,
  Pill,
  RefreshCw,
  SquarePen,
  TriangleAlert,
} from "lucide-react"
import { Link, useLocation, useNavigate, useParams } from "react-router-dom"

import { EmptyState } from "@/components/app/empty-state"
import { FeedbackBanner } from "@/components/app/feedback-banner"
import { PageHeader } from "@/components/app/page-header"
import { CalculationDoseStateBadge } from "@/components/app/calculation-dose-state-badge"
import { CalculationStatusBadge } from "@/components/app/calculation-status-badge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { getAdministrationDayStatusMeta } from "@/features/calculation/calculation-dose-state"
import {
  getPatientActiveItems,
  getPatientConsumptionSummary,
  getPatientDoseSchedule,
  getPatientDetails,
} from "@/features/patients/patient-service"
import {
  formatExpectedRange,
  getComparisonWindowDescription,
  getComparisonWindowLabel,
  getUsageModeDescription,
  getUsageModeLabel,
} from "@/features/prescriptions/prescription-presentation"
import { useAuth } from "@/features/auth/use-auth"
import { formatDecimalAsInteger, formatSignedDecimalAsInteger } from "@/lib/utils"
import { HttpError } from "@/services/http"
import type {
  CalculationAdministrationDayStatus,
  CalculationDoseOccurrence,
} from "@/types/calculation"
import type {
  PatientActiveItem,
  PatientDoseSchedule,
  PatientConsumptionProjection,
  PatientConsumptionSummary,
  PatientDetails,
} from "@/types/patient"

type DetailLocationState = {
  message?: string
  tone?: "success" | "error"
}

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível carregar o detalhe do paciente."
}

function formatDate(value: string | null) {
  if (!value) {
    return "Não informada"
  }

  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`))
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { timeStyle: "short" }).format(new Date(value))
}

function getItemTypeLabel(itemType: PatientActiveItem["item_type"]) {
  return itemType === "medication" ? "Medicamento" : "Insumo"
}

function getDivergenceLabel(
  divergenceStatus: PatientConsumptionProjection["divergence_status"],
) {
  switch (divergenceStatus) {
    case "above_expected":
      return "Acima do esperado"
    case "below_expected":
      return "Abaixo do esperado"
    case "coherent":
      return "Coerente"
    default:
      return "Sem base suficiente"
  }
}

function getDivergenceVariant(
  divergenceStatus: PatientConsumptionProjection["divergence_status"],
) {
  switch (divergenceStatus) {
    case "above_expected":
    case "below_expected":
      return "warning" as const
    case "coherent":
      return "success" as const
    default:
      return "outline" as const
  }
}

function formatProjectionMetric(
  value: string | null,
  unitSymbol?: string | null,
) {
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

function isScheduledDoseProjection(projection: PatientConsumptionProjection) {
  return (
    projection.comparison_window === "scheduled_times" &&
    (projection.dose_occurrences?.length ?? 0) > 0
  )
}

function shouldShowLegacyCalculationStatusBadge(
  projection: PatientConsumptionProjection,
) {
  if (!isScheduledDoseProjection(projection)) {
    return true
  }

  return (
    projection.status === "low_stock" ||
    projection.status === "critical_stock" ||
    projection.status === "inconsistent_data" ||
    projection.status === "invalid_prescription"
  )
}

function getDoseOccurrenceSupportText(occurrence: CalculationDoseOccurrence) {
  if (occurrence.state === "completed" && occurrence.matched_occurred_at) {
    return `Registrada às ${formatTime(occurrence.matched_occurred_at)}.`
  }

  if (occurrence.state === "due_now") {
    return `Janela aberta até ${formatTime(occurrence.tolerated_until)}.`
  }

  if (occurrence.state === "overdue") {
    return `Tolerância encerrada às ${formatTime(occurrence.tolerated_until)}.`
  }

  return `Prevista para ${formatTime(occurrence.scheduled_at)}.`
}

function getAdministrationDayStatusBadge(
  status: CalculationAdministrationDayStatus | null,
) {
  if (!status) {
    return null
  }

  const meta = getAdministrationDayStatusMeta(status)
  return <Badge variant={meta.variant}>{meta.label}</Badge>
}

export function PatientDetailPage() {
  const { patientId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { token } = useAuth()

  const [patient, setPatient] = useState<PatientDetails | null>(null)
  const [activeItems, setActiveItems] = useState<PatientActiveItem[]>([])
  const [consumptionSummary, setConsumptionSummary] = useState<PatientConsumptionSummary | null>(null)
  const [doseSchedule, setDoseSchedule] = useState<PatientDoseSchedule | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [consumptionError, setConsumptionError] = useState<string | null>(null)
  const [doseScheduleError, setDoseScheduleError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const flashState = location.state as DetailLocationState | null
  const uniqueActiveItems = useMemo(() => {
    const uniqueItems = new Map<string, PatientActiveItem>()

    for (const activeItem of activeItems) {
      if (!uniqueItems.has(activeItem.item_id)) {
        uniqueItems.set(activeItem.item_id, activeItem)
      }
    }

    return Array.from(uniqueItems.values())
  }, [activeItems])

  const consumptionOperationalSummary = useMemo(() => {
    if (!consumptionSummary) {
      return null
    }

    const criticalItems = consumptionSummary.items.filter(
      (projection) => projection.status === "critical_stock",
    ).length

    const divergencesDetected = consumptionSummary.items.filter(
      (projection) =>
        projection.divergence_status === "above_expected" ||
        projection.divergence_status === "below_expected",
    ).length

    return {
      criticalItems,
      divergencesDetected,
      invalidItems: consumptionSummary.invalid_items,
      itemsAtRisk: consumptionSummary.items_requiring_attention,
      totalItems: consumptionSummary.total_items,
    }
  }, [consumptionSummary])
  const consumptionProjectionByItemId = useMemo(
    () =>
      new Map(
        consumptionSummary?.items.map((projection) => [projection.item_id, projection]) ?? [],
      ),
    [consumptionSummary],
  )
  const activeItemByItemId = useMemo(
    () =>
      new Map(activeItems.map((activeItem) => [activeItem.item_id, activeItem])),
    [activeItems],
  )
  const loadPatient = useCallback(async () => {
    if (!token || !patientId) {
      setError("Não foi possível identificar o paciente ou a sessão atual.")
      setPatient(null)
      setActiveItems([])
      setConsumptionSummary(null)
      setDoseSchedule(null)
      setConsumptionError(null)
      setDoseScheduleError(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const [
        detailsResult,
        activeItemsResult,
        consumptionResult,
        doseScheduleResult,
      ] = await Promise.allSettled([
        getPatientDetails(token, patientId),
        getPatientActiveItems(token, patientId),
        getPatientConsumptionSummary(token, patientId),
        getPatientDoseSchedule(token, patientId),
      ])

      if (detailsResult.status !== "fulfilled") {
        throw detailsResult.reason
      }

      if (activeItemsResult.status !== "fulfilled") {
        throw activeItemsResult.reason
      }

      setPatient(detailsResult.value.data)
      setActiveItems(activeItemsResult.value.data)

      if (consumptionResult.status === "fulfilled") {
        setConsumptionSummary(consumptionResult.value.data)
        setConsumptionError(null)
      } else {
        setConsumptionSummary(null)
        setConsumptionError(getErrorMessage(consumptionResult.reason))
      }

      if (doseScheduleResult.status === "fulfilled") {
        setDoseSchedule(doseScheduleResult.value.data)
        setDoseScheduleError(null)
      } else {
        setDoseSchedule(null)
        setDoseScheduleError(getErrorMessage(doseScheduleResult.reason))
      }
    } catch (requestError) {
      setPatient(null)
      setActiveItems([])
      setConsumptionSummary(null)
      setDoseSchedule(null)
      setConsumptionError(null)
      setDoseScheduleError(null)
      setError(getErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [patientId, token])

  useEffect(() => {
    void loadPatient()
  }, [loadPatient])

  useEffect(() => {
    if (!flashState?.message) {
      return
    }

    navigate(location.pathname, { replace: true })
  }, [flashState?.message, location.pathname, navigate])

  return (
    <div className="grid gap-6">
      <PageHeader
        actions={
          <>
            <Button asChild variant="outline">
              <Link to="/patients">
                <ArrowLeft className="h-4 w-4" />
                Voltar
              </Link>
            </Button>
            <Button disabled={isLoading} onClick={() => void loadPatient()} variant="outline">
              <RefreshCw className="h-4 w-4" />
              Atualizar
            </Button>
            {patient ? (
              <Button asChild>
                <Link to={`/patients/${patient.id}/edit`}>
                  <SquarePen className="h-4 w-4" />
                  Editar
                </Link>
              </Button>
            ) : null}
          </>
        }
        description="Veja as principais informações do paciente, seus itens em uso e os registros recentes."
        title="Detalhe do paciente"
      />

      {flashState?.message ? (
        <FeedbackBanner
          message={flashState.message}
          variant={flashState.tone === "success" ? "success" : "error"}
        />
      ) : null}

      {error ? <FeedbackBanner message={error} variant="error" /> : null}

      {isLoading ? (
        <div className="rounded-2xl border border-border/80 bg-white/92 px-6 py-10 text-sm text-muted-foreground">
          Carregando detalhe do paciente...
        </div>
      ) : null}

      {patient ? (
        <>
          <section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
            <Card className="bg-white/92">
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle>{patient.full_name}</CardTitle>
                    <CardDescription>Nascimento: {formatDate(patient.birth_date)}</CardDescription>
                  </div>
                  <Badge variant={patient.is_active ? "success" : "outline"}>
                    {patient.is_active ? "Ativo" : "Inativo"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                    <p className="text-muted-foreground">Nascimento</p>
                    <p className="mt-2 font-medium">{formatDate(patient.birth_date)}</p>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                    <p className="text-muted-foreground">Situação</p>
                    <p className="mt-2 font-medium">{patient.is_active ? "Paciente ativo" : "Paciente inativo"}</p>
                  </div>
                </div>
                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                  <p className="font-medium">Observações</p>
                  <p className="mt-2 text-muted-foreground">{patient.care_notes?.trim() || "Sem observações cadastradas."}</p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/92">
              <CardHeader>
                <CardTitle>Resumo operacional</CardTitle>
                <CardDescription>Indicadores principais para acompanhar a rotina do paciente.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3">
                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                  <p className="text-sm text-muted-foreground">Prescrições ativas</p>
                  <p className="text-2xl font-semibold">{patient.metrics.active_prescriptions}</p>
                </div>
                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                  <p className="text-sm text-muted-foreground">Itens ativos</p>
                  <p className="text-2xl font-semibold">{patient.metrics.active_items}</p>
                </div>
                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                  <p className="text-sm text-muted-foreground">Alertas abertos</p>
                  <p className="text-2xl font-semibold">{patient.metrics.open_alerts}</p>
                </div>
              </CardContent>
            </Card>
          </section>

          <section>
            <Card className="bg-white/92">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock3 className="h-4 w-4 text-primary" />
                  Agenda de doses do dia
                </CardTitle>
                <CardDescription>
                  Veja o que já foi administrado, o que ainda não chegou no horário e o que está realmente atrasado.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                {doseScheduleError ? (
                  <FeedbackBanner
                    message={doseScheduleError}
                    title="Não foi possível carregar a agenda de doses"
                    variant="error"
                  />
                ) : null}

                {!doseScheduleError && doseSchedule ? (
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                    <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">
                        Doses do dia
                      </p>
                      <p className="mt-2 text-2xl font-semibold">{doseSchedule.total_doses}</p>
                    </div>
                    <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">
                        Concluidas
                      </p>
                      <p className="mt-2 text-2xl font-semibold">{doseSchedule.completed_dose_count}</p>
                    </div>
                    <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">
                        Na janela
                      </p>
                      <p className="mt-2 text-2xl font-semibold">{doseSchedule.due_now_dose_count}</p>
                    </div>
                    <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">
                        Atrasadas
                      </p>
                      <p className="mt-2 text-2xl font-semibold">{doseSchedule.overdue_dose_count}</p>
                    </div>
                    <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">
                        Próxima dose
                      </p>
                      <p className="mt-2 font-semibold">
                        {doseSchedule.next_dose
                          ? `${doseSchedule.next_dose.item_name} as ${formatTime(doseSchedule.next_dose.scheduled_at)}`
                          : "Sem dose futura hoje"}
                      </p>
                    </div>
                  </div>
                ) : null}

                {!doseScheduleError && doseSchedule?.total_doses === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
                    <EmptyState
                      description="A agenda do dia aparece aqui quando existem prescrições fixas com horarios definidos."
                      icon={Clock3}
                      title="Nenhuma dose programada hoje"
                    />
                  </div>
                ) : null}

                {!doseScheduleError && doseSchedule && doseSchedule.total_doses > 0 ? (
                  <div className="space-y-3">
                    {doseSchedule.doses.map((dose, index) => (
                      <div
                        className="rounded-2xl border border-border/70 bg-secondary/35 p-4"
                        key={`${dose.item_id}-${dose.prescription_id ?? "prescription"}-${dose.scheduled_at}-${index}`}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{dose.item_name}</p>
                            <p className="text-muted-foreground">
                              Prevista as {formatTime(dose.scheduled_at)}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <CalculationDoseStateBadge state={dose.state} />
                            {doseSchedule.next_dose?.scheduled_at === dose.scheduled_at &&
                            doseSchedule.next_dose?.item_id === dose.item_id ? (
                              <Badge variant="outline">Próxima</Badge>
                            ) : null}
                          </div>
                        </div>

                        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                          <div>
                            <p className="text-muted-foreground">Dose</p>
                            <p className="font-medium text-foreground">
                              {formatProjectionMetric(dose.dose_amount, dose.unit_symbol)}
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Tolerancia até</p>
                            <p className="font-medium text-foreground">
                              {formatTime(dose.tolerated_until)}
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Situação do item</p>
                            <p className="font-medium text-foreground">
                              {dose.administration_day_status
                                ? getAdministrationDayStatusMeta(dose.administration_day_status).label
                                : "Sem classificacao"}
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Registro</p>
                            <p className="font-medium text-foreground">
                              {dose.matched_occurred_at
                                ? `As ${formatTime(dose.matched_occurred_at)}`
                                : "Ainda não registrado"}
                            </p>
                          </div>
                        </div>

                        <p className="mt-3 text-muted-foreground">
                          {getDoseOccurrenceSupportText(dose)}
                          {dose.administration_day_reason
                            ? ` ${dose.administration_day_reason}`
                            : ""}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-6 xl:grid-cols-2">
            <Card className="bg-white/92">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TriangleAlert className="h-4 w-4 text-primary" />
                  Projeções de consumo
                </CardTitle>
                <CardDescription>
                  Acompanhe o consumo previsto, o saldo atual e os sinais de atenção dos itens em uso.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {consumptionError ? (
                  <FeedbackBanner
                    message={consumptionError}
                    title="Não foi possível carregar a projeção do paciente"
                    variant="error"
                  />
                ) : null}

                {!consumptionError && consumptionSummary && consumptionOperationalSummary ? (
                  <div className="space-y-3">
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">
                          Itens ativos
                        </p>
                        <p className="mt-2 text-2xl font-semibold">
                          {consumptionOperationalSummary.totalItems}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">
                          Itens em risco
                        </p>
                        <p className="mt-2 text-2xl font-semibold">
                          {consumptionOperationalSummary.itemsAtRisk}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">
                          Itens críticos
                        </p>
                        <p className="mt-2 text-2xl font-semibold">
                          {consumptionOperationalSummary.criticalItems}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">
                          Divergencias detectadas
                        </p>
                        <p className="mt-2 text-2xl font-semibold">
                          {consumptionOperationalSummary.divergencesDetected}
                        </p>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-border/70 bg-secondary/20 px-4 py-3 text-sm text-muted-foreground">
                      Resumo gerado em {formatDate(consumptionSummary.reference_date)}.
                      {consumptionOperationalSummary.invalidItems > 0
                        ? ` ${consumptionOperationalSummary.invalidItems} item(ns) sem base suficiente para cálculo.`
                        : " Todos os itens retornados possuem base suficiente para acompanhamento."}
                    </div>
                  </div>
                ) : null}

                {!consumptionError && consumptionSummary?.items.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
                    <EmptyState
                      description="As projeções aparecem aqui quando o paciente tem prescrições ativas."
                      icon={TriangleAlert}
                      title="Nenhuma projeção disponível"
                    />
                  </div>
                ) : null}

                {consumptionSummary?.items.map((projection) => (
                  <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4" key={projection.item_id}>
                    {(() => {
                      const activeItem = activeItemByItemId.get(projection.item_id)
                      const scheduleTracked = isScheduledDoseProjection(projection)
                      const administrationDayMeta = projection.administration_day_status
                        ? getAdministrationDayStatusMeta(projection.administration_day_status)
                        : null

                      return (
                        <>
                    <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-medium">{projection.item_name}</p>
                        <p className="text-muted-foreground">
                          Consumo diario previsto: {formatProjectionMetric(projection.daily_consumption, projection.unit_symbol)}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {shouldShowLegacyCalculationStatusBadge(projection) ? (
                          <CalculationStatusBadge status={projection.status} />
                        ) : null}
                        {scheduleTracked && administrationDayMeta ? (
                          <Badge variant={administrationDayMeta.variant}>
                            {administrationDayMeta.label}
                          </Badge>
                        ) : (
                          <Badge variant={getDivergenceVariant(projection.divergence_status)}>
                            {getDivergenceLabel(projection.divergence_status)}
                          </Badge>
                        )}
                      </div>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                      <div>
                        <p className="text-muted-foreground">Saldo atual</p>
                        <p className="font-medium text-foreground">
                          {formatProjectionMetric(projection.current_stock, projection.unit_symbol)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Cobertura estimada</p>
                        <p className="font-medium text-foreground">
                          {formatDaysRemaining(projection.days_remaining)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Esperado até agora</p>
                        <p className="font-medium text-foreground">
                          {formatProjectionMetric(projection.expected_consumption_until_now, projection.unit_symbol)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Realizado até agora</p>
                        <p className="font-medium text-foreground">
                          {formatProjectionMetric(projection.actual_consumption_until_now, projection.unit_symbol)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                      <div>
                        <p className="text-muted-foreground">Tipo de uso</p>
                        <p className="font-medium text-foreground">
                          {getUsageModeLabel(projection.usage_mode)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {getUsageModeDescription(projection.usage_mode)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Lógica de comparação</p>
                        <p className="font-medium text-foreground">
                          {getComparisonWindowLabel(projection.comparison_window)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {getComparisonWindowDescription(projection.comparison_window)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Faixa esperada</p>
                        <p className="font-medium text-foreground">
                          {formatExpectedRange(
                            activeItem?.min_expected_per_day ?? null,
                            activeItem?.max_expected_per_day ?? null,
                            projection.unit_symbol,
                          )}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">
                          {scheduleTracked ? "Situação do dia" : "Divergencia"}
                        </p>
                        <p className="font-medium text-foreground">
                          {scheduleTracked
                            ? administrationDayMeta?.label || "Sem classificacao"
                            : projection.divergence
                              ? `${formatSignedDecimalAsInteger(projection.divergence)} ${projection.unit_symbol}`
                              : "Não disponível"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {scheduleTracked
                            ? projection.administration_day_reason || "Agenda avaliada por horario."
                            : getDivergenceLabel(projection.divergence_status)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Acompanhamento</p>
                        <p className="font-medium text-foreground">
                          {(scheduleTracked
                            ? projection.administration_day_reason
                            : projection.alert_reason) || "Sem observações adicionais."}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-border/70 bg-background/80 p-3">
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Activity className="h-4 w-4" />
                          <p className="text-sm">Status operacional</p>
                        </div>
                        <p className="mt-2 font-medium text-foreground">
                          {projection.is_valid
                            ? "Dados consistentes para acompanhamento."
                            : projection.invalid_reason || "Dados insuficientes para calcular."}
                        </p>
                      </div>
                    </div>

                    {scheduleTracked && projection.dose_occurrences?.length ? (
                      <div className="mt-4 rounded-2xl border border-border/70 bg-background/80 p-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <p className="font-medium">Doses previstas hoje</p>
                            <p className="text-sm text-muted-foreground">
                              O paciente so fica em atraso quando a dose sai da janela de tolerancia.
                            </p>
                          </div>
                          {projection.dose_schedule ? (
                            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                              <Badge variant="outline">
                                {projection.dose_schedule.completed_dose_count} concluidas
                              </Badge>
                              <Badge variant="outline">
                                {projection.dose_schedule.due_now_dose_count} na janela
                              </Badge>
                              <Badge variant="outline">
                                {projection.dose_schedule.overdue_dose_count} atrasadas
                              </Badge>
                            </div>
                          ) : null}
                        </div>
                        <div className="mt-4 grid gap-2">
                          {projection.dose_occurrences.map((occurrence, index) => (
                            <div
                              className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/60 bg-secondary/25 px-3 py-2"
                              key={`${projection.item_id}-${occurrence.prescription_id ?? "prescription"}-${occurrence.scheduled_at}-${index}`}
                            >
                              <div>
                                <p className="font-medium">
                                  {formatTime(occurrence.scheduled_at)}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  {getDoseOccurrenceSupportText(occurrence)}
                                </p>
                              </div>
                              <CalculationDoseStateBadge state={occurrence.state} />
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    <div className="mt-4">
                      <Button asChild size="sm" variant="outline">
                        <Link to={`/items/${projection.item_id}`}>
                          Ver situação do item
                        </Link>
                      </Button>
                    </div>
                        </>
                      )
                    })()}
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="bg-white/92">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ClipboardList className="h-4 w-4 text-primary" />
                  Prescrições ativas
                </CardTitle>
                <CardDescription>Lista dos tratamentos em andamento para este paciente.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {activeItems.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
                    <EmptyState
                      description="Cadastre uma prescrição para ver o fluxo operacional deste paciente."
                      icon={ClipboardList}
                      title="Nenhuma prescrição ativa"
                    />
                  </div>
                ) : (
                  activeItems.map((activeItem) => {
                    const projection = consumptionProjectionByItemId.get(activeItem.item_id)

                    return (
                    <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4" key={activeItem.prescription_id}>
                      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-medium">{activeItem.item_name}</p>
                          <p className="text-muted-foreground">
                            Dose {formatDecimalAsInteger(activeItem.dose_amount)} | {activeItem.frequency_per_day}x ao dia
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {projection && shouldShowLegacyCalculationStatusBadge(projection) ? (
                            <CalculationStatusBadge status={projection.status} />
                          ) : null}
                          {projection?.administration_day_status
                            ? getAdministrationDayStatusBadge(projection.administration_day_status)
                            : null}
                          <Badge variant={activeItem.is_below_minimum ? "warning" : "success"}>
                            {activeItem.is_below_minimum ? "Estoque baixo" : "Estoque ok"}
                          </Badge>
                        </div>
                      </div>
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                        <div>
                          <p className="text-muted-foreground">Horarios</p>
                          <p className="font-medium text-foreground">
                            {activeItem.specific_times?.join(", ") || "Não informados"}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Período</p>
                          <p className="font-medium text-foreground">
                            {formatDate(activeItem.start_date)}{" "}
                            {activeItem.end_date ? `até ${formatDate(activeItem.end_date)}` : "sem data final"}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Duracao estimada</p>
                          <p className="font-medium text-foreground">
                            {formatDaysRemaining(projection?.days_remaining ?? null)}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Tipo de uso</p>
                          <p className="font-medium text-foreground">
                            {getUsageModeLabel(activeItem.usage_mode)}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Lógica de comparação</p>
                          <p className="font-medium text-foreground">
                            {getComparisonWindowLabel(activeItem.comparison_window)}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Faixa esperada</p>
                          <p className="font-medium text-foreground">
                            {formatExpectedRange(
                              activeItem.min_expected_per_day,
                              activeItem.max_expected_per_day,
                              activeItem.unit_symbol,
                            )}
                          </p>
                        </div>
                      </div>
                      <div className="mt-4 grid gap-3 sm:grid-cols-2">
                        <div>
                          <p className="text-muted-foreground">Consumo diario previsto</p>
                          <p className="font-medium text-foreground">
                            {formatProjectionMetric(
                              projection?.daily_consumption ?? null,
                              projection?.unit_symbol ?? activeItem.unit_symbol,
                            )}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Acompanhamento</p>
                          <p className="font-medium text-foreground">
                            {(projection && isScheduledDoseProjection(projection)
                              ? projection.administration_day_reason
                              : projection?.alert_reason) || "Sem observações adicionais."}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {projection?.dose_schedule?.next_dose
                              ? `Próxima dose as ${formatTime(projection.dose_schedule.next_dose.scheduled_at)}.`
                              : getUsageModeDescription(activeItem.usage_mode)}
                          </p>
                        </div>
                      </div>
                      <div className="mt-4">
                        <Button asChild size="sm" variant="outline">
                          <Link to={`/prescriptions/${activeItem.prescription_id}/edit?patientId=${patient.id}`}>
                            <SquarePen className="h-4 w-4" />
                            Editar prescrição
                          </Link>
                        </Button>
                      </div>
                    </div>
                  )})
                )}
              </CardContent>
            </Card>

            <Card className="bg-white/92">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Pill className="h-4 w-4 text-primary" />
                  Itens ativos do paciente
                </CardTitle>
                <CardDescription>Resumo dos itens em uso e da disponibilidade atual.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {uniqueActiveItems.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
                    <EmptyState
                      description="Os itens ativos aparecem aqui quando existem prescrições em andamento."
                      icon={Pill}
                      title="Nenhum item ativo"
                    />
                  </div>
                ) : (
                  uniqueActiveItems.map((activeItem) => (
                    <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4" key={activeItem.item_id}>
                      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-medium">{activeItem.item_name}</p>
                          <p className="text-muted-foreground">
                            {getItemTypeLabel(activeItem.item_type)} | Unidade {activeItem.unit_symbol}
                          </p>
                        </div>
                        <Badge variant={activeItem.is_below_minimum ? "warning" : "outline"}>
                          {activeItem.is_below_minimum ? "Abaixo do minimo" : "Disponível"}
                        </Badge>
                      </div>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div>
                          <p className="text-muted-foreground">Estoque atual</p>
                          <p className="font-medium text-foreground">
                            {formatDecimalAsInteger(activeItem.current_stock)} {activeItem.unit_symbol}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Estoque minimo</p>
                          <p className="font-medium text-foreground">
                            {formatDecimalAsInteger(activeItem.minimum_stock)} {activeItem.unit_symbol}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-6 xl:grid-cols-2">
            <Card className="bg-white/92">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-4 w-4 text-primary" />
                  Alertas abertos
                </CardTitle>
                <CardDescription>Alertas que merecem atenção no acompanhamento do paciente.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {patient.open_alerts.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
                    <EmptyState
                      description="Quando houver alertas vinculados ao paciente, eles aparecerao aqui."
                      icon={Bell}
                      title="Nenhum alerta aberto"
                    />
                  </div>
                ) : (
                  patient.open_alerts.map((alert) => (
                    <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4" key={alert.id}>
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <p className="font-medium">{alert.title}</p>
                        <Badge variant="warning">{alert.severity}</Badge>
                      </div>
                      <p className="text-muted-foreground">{alert.message}</p>
                      <p className="mt-3 text-xs text-muted-foreground">{formatDateTime(alert.created_at)}</p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card className="bg-white/92">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock3 className="h-4 w-4 text-primary" />
                  Movimentações recentes
                </CardTitle>
                <CardDescription>Registros recentes relacionados aos itens usados por este paciente.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {patient.recent_movements.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
                    <EmptyState
                      description="As ultimas administrações e outras movimentacoes deste paciente aparecerao aqui."
                      icon={Clock3}
                      title="Nenhuma movimentacao recente"
                    />
                  </div>
                ) : (
                  patient.recent_movements.map((movement) => (
                    <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4" key={movement.id}>
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <p className="font-medium">{movement.item_name}</p>
                        <Badge variant="outline">{movement.movement_type}</Badge>
                      </div>
                      <p className="text-muted-foreground">
                        Quantidade: {formatDecimalAsInteger(movement.quantity)} {movement.unit_symbol}
                      </p>
                      <p className="mt-3 text-xs text-muted-foreground">{formatDateTime(movement.occurred_at)}</p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </section>
        </>
      ) : null}
    </div>
  )
}
