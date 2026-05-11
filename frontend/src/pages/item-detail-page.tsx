import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Activity,
  ArrowLeft,
  Bell,
  RefreshCw,
  ShieldAlert,
  SquarePen,
} from "lucide-react"
import { Link, useParams } from "react-router-dom"

import { EmptyState } from "@/components/app/empty-state"
import { FeedbackBanner } from "@/components/app/feedback-banner"
import { PageHeader } from "@/components/app/page-header"
import { CalculationStatusBadge } from "@/components/app/calculation-status-badge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/features/auth/use-auth"
import {
  getItemAlertCandidates,
  getItemProjection,
} from "@/features/calculation/calculation-service"
import { getItem } from "@/features/items/item-service"
import { getItemStock } from "@/features/inventory/inventory-service"
import {
  formatExpectedRange,
  getComparisonWindowDescription,
  getComparisonWindowLabel,
  getUsageModeDescription,
  getUsageModeLabel,
} from "@/features/prescriptions/prescription-presentation"
import { formatDecimalAsInteger, formatSignedDecimalAsInteger } from "@/lib/utils"
import { HttpError } from "@/services/http"
import type { CalculationAlertCandidate, CalculationItemProjection } from "@/types/calculation"
import type { Item } from "@/types/item"
import type { ItemStock } from "@/types/inventory"

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível carregar a situação do item."
}

function getItemTypeLabel(itemType: Item["item_type"]) {
  return itemType === "medication" ? "Medicamento" : "Insumo"
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

function getItemSignalVariant(
  stock: ItemStock | null,
  candidates: CalculationAlertCandidate[],
) {
  if (candidates.some((candidate) => candidate.status === "critical_stock")) {
    return "danger" as const
  }

  if (stock?.is_below_minimum || candidates.length > 0) {
    return "warning" as const
  }

  return "success" as const
}

function getItemSignalLabel(
  stock: ItemStock | null,
  candidates: CalculationAlertCandidate[],
) {
  if (candidates.some((candidate) => candidate.status === "critical_stock")) {
    return "Atenção imediata"
  }

  if (stock?.is_below_minimum || candidates.length > 0) {
    return "Acompanhamento recomendado"
  }

  return "Situação estavel"
}

export function ItemDetailPage() {
  const { itemId } = useParams()
  const { token } = useAuth()

  const [item, setItem] = useState<Item | null>(null)
  const [stock, setStock] = useState<ItemStock | null>(null)
  const [projection, setProjection] = useState<CalculationItemProjection | null>(null)
  const [alertCandidates, setAlertCandidates] = useState<CalculationAlertCandidate[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const signalVariant = useMemo(
    () => getItemSignalVariant(stock, alertCandidates),
    [alertCandidates, stock],
  )

  const signalLabel = useMemo(
    () => getItemSignalLabel(stock, alertCandidates),
    [alertCandidates, stock],
  )

  const loadItemSituation = useCallback(async () => {
    if (!token || !itemId) {
      setError("Não foi possível identificar o item ou a sessão atual.")
      setItem(null)
      setStock(null)
      setProjection(null)
      setAlertCandidates([])
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const [itemResponse, stockResponse, projectionResponse, candidatesResponse] =
        await Promise.all([
          getItem(token, itemId),
          getItemStock(token, itemId),
          getItemProjection(token, itemId),
          getItemAlertCandidates(token, itemId, { limit: 100 }),
        ])

      setItem(itemResponse.data)
      setStock(stockResponse.data)
      setProjection(projectionResponse.data)
      setAlertCandidates(candidatesResponse.data)
    } catch (requestError) {
      setItem(null)
      setStock(null)
      setProjection(null)
      setAlertCandidates([])
      setError(getErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [itemId, token])

  useEffect(() => {
    void loadItemSituation()
  }, [loadItemSituation])

  return (
    <div className="grid gap-6">
      <PageHeader
        actions={
          <>
            <Button asChild variant="outline">
              <Link to="/items">
                <ArrowLeft className="h-4 w-4" />
                Voltar
              </Link>
            </Button>
            <Button disabled={isLoading} onClick={() => void loadItemSituation()} variant="outline">
              <RefreshCw className="h-4 w-4" />
              Atualizar
            </Button>
            {item ? (
              <Button asChild>
                <Link to={`/items/${item.id}/edit`}>
                  <SquarePen className="h-4 w-4" />
                  Editar
                </Link>
              </Button>
            ) : null}
          </>
        }
        description="Consulte estoque, projeção consolidada e sinais operacionais deste item."
        title="Situação do item"
      />

      {error ? <FeedbackBanner message={error} variant="error" /> : null}

      {isLoading ? (
        <div className="rounded-2xl border border-border/80 bg-white/92 px-6 py-10 text-sm text-muted-foreground">
          Carregando situação do item...
        </div>
      ) : null}

      {item && stock && projection ? (
        <>
          <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <Card className="bg-white/92">
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle>{item.name}</CardTitle>
                    <CardDescription>
                      {getItemTypeLabel(item.item_type)} • {stock.unit_name} ({stock.unit_symbol})
                    </CardDescription>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant={item.is_active ? "success" : "outline"}>
                      {item.is_active ? "Ativo" : "Inativo"}
                    </Badge>
                    <Badge variant={signalVariant}>{signalLabel}</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <p className="min-h-12 text-muted-foreground">
                  {item.description?.trim() || "Sem descrição cadastrada."}
                </p>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                      Saldo atual
                    </p>
                    <p className="mt-2 text-2xl font-semibold">
                      {formatProjectionMetric(stock.current_stock, stock.unit_symbol)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                      Estoque mínimo
                    </p>
                    <p className="mt-2 text-2xl font-semibold">
                      {formatProjectionMetric(stock.minimum_stock, stock.unit_symbol)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                      Cobertura estimada
                    </p>
                    <p className="mt-2 text-2xl font-semibold">
                      {formatDaysRemaining(projection.metrics.days_remaining)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                      Prescrições ativas
                    </p>
                    <p className="mt-2 text-2xl font-semibold">
                      {projection.metrics.active_prescriptions}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/92">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-primary" />
                  Projeção consolidada
                </CardTitle>
                <CardDescription>
                  Indicadores do motor para acompanhar cobertura e consumo recente.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 text-sm">
                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                  <p className="text-muted-foreground">Consumo diário previsto</p>
                  <p className="mt-2 font-medium">
                    {formatProjectionMetric(
                      projection.metrics.predicted_daily_consumption,
                      projection.unit_symbol,
                    )}
                  </p>
                </div>
                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                  <p className="text-muted-foreground">Consumo realizado recente</p>
                  <p className="mt-2 font-medium">
                    {formatProjectionMetric(
                      projection.metrics.realized_daily_average,
                      projection.unit_symbol,
                    )}
                  </p>
                </div>
                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                  <p className="text-muted-foreground">Diferença consolidada</p>
                  <p className="mt-2 font-medium">
                    {projection.divergence.quantity_gap
                      ? `${formatSignedDecimalAsInteger(projection.divergence.quantity_gap)} ${projection.unit_symbol}`
                      : "Não disponível"}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {projection.divergence.percent_gap
                      ? `${formatSignedDecimalAsInteger(projection.divergence.percent_gap)}% em relacao ao previsto`
                      : "Sem base suficiente para comparar."}
                  </p>
                </div>
                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
                  <p className="text-muted-foreground">Sinal do motor</p>
                  <p className="mt-2 font-medium">
                    {alertCandidates.length > 0
                      ? `${alertCandidates.length} projeção(ões) exigem atenção`
                      : "Nenhum alerta operacional para este item"}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Atualizado com base no saldo e nas prescrições em andamento.
                  </p>
                </div>
              </CardContent>
            </Card>
          </section>

          <Card className="bg-white/92">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-4 w-4 text-primary" />
                Situações operacionais do item
              </CardTitle>
              <CardDescription>
                Casos em que este item exige acompanhamento no contexto dos pacientes atendidos.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {alertCandidates.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
                  <EmptyState
                    description="Quando o motor identificar risco operacional relacionado a este item, os detalhes aparecerão aqui."
                    icon={ShieldAlert}
                    title="Nenhum sinal operacional no momento"
                  />
                </div>
              ) : (
                alertCandidates.map((candidate) => (
                  <div
                    className="rounded-2xl border border-border/70 bg-secondary/35 p-4"
                    key={`${candidate.patient_id}-${candidate.item_id}`}
                  >
                    <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-medium">{candidate.patient_name || "Paciente não identificado"}</p>
                        <p className="text-muted-foreground">
                          Consumo diário:{" "}
                          {formatProjectionMetric(
                            candidate.daily_consumption,
                            candidate.unit_symbol,
                          )}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <CalculationStatusBadge status={candidate.status} />
                        {candidate.should_alert ? (
                          <Badge variant="warning">Requer atenção</Badge>
                        ) : null}
                      </div>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                      <div>
                        <p className="text-muted-foreground">Saldo atual</p>
                        <p className="font-medium text-foreground">
                          {formatProjectionMetric(
                            candidate.current_stock,
                            candidate.unit_symbol,
                          )}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Cobertura estimada</p>
                        <p className="font-medium text-foreground">
                          {formatDaysRemaining(candidate.days_remaining)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Divergência</p>
                        <p className="font-medium text-foreground">
                          {candidate.divergence
                            ? `${formatSignedDecimalAsInteger(candidate.divergence)} ${candidate.unit_symbol}`
                            : "Não disponível"}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Motivo</p>
                        <p className="font-medium text-foreground">
                          {candidate.alert_reason || "Sem observações adicionais."}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Tipo de uso</p>
                        <p className="font-medium text-foreground">
                          {getUsageModeLabel(candidate.usage_mode)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {getUsageModeDescription(candidate.usage_mode)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Comparação</p>
                        <p className="font-medium text-foreground">
                          {getComparisonWindowLabel(candidate.comparison_window)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {getComparisonWindowDescription(candidate.comparison_window)}
                        </p>
                      </div>
                      <div className="sm:col-span-2 xl:col-span-2">
                        <p className="text-muted-foreground">Faixa esperada</p>
                        <p className="font-medium text-foreground">
                          {formatExpectedRange(
                            candidate.min_expected_per_day,
                            candidate.max_expected_per_day,
                            candidate.unit_symbol,
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4">
                      <Button asChild size="sm" variant="outline">
                        <Link to={`/patients/${candidate.patient_id}`}>Ver paciente</Link>
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  )
}
