import { useCallback, useEffect, useState } from "react"
import {
  Activity,
  AlertTriangle,
  Archive,
  ClipboardList,
  Package,
  RefreshCcw,
  ShieldCheck,
  TriangleAlert,
  Users,
} from "lucide-react"
import { Link } from "react-router-dom"

import { EmptyState } from "@/components/app/empty-state"
import { FeedbackBanner } from "@/components/app/feedback-banner"
import { CalculationDivergenceList } from "@/components/app/calculation-divergence-list"
import { CalculationStatusLegend } from "@/components/app/calculation-status-legend"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { getAlertsSummaryWithFallback } from "@/features/alerts/alert-service"
import {
  getDashboardOverview,
  getDashboardSummary,
} from "@/features/dashboard/dashboard-service"
import { getRelevantDivergenceCandidates as getRelevantDivergenceCandidatesFromCalculation } from "@/features/calculation/calculation-service"
import { useAuth } from "@/features/auth/use-auth"
import { HttpError } from "@/services/http"
import type { AlertSummary } from "@/types/alert"
import type {
  DashboardCalculationSummary,
  DashboardOverview,
  DashboardSummary,
} from "@/types/dashboard"
import type { CalculationAlertCandidate } from "@/types/calculation"

const summaryCards = [
  {
    description: "Pacientes atualmente ativos no sistema.",
    icon: Users,
    key: "active_patients",
    label: "Pacientes ativos",
  },
  {
    description: "Medicamentos e insumos cadastrados como ativos.",
    icon: Archive,
    key: "active_items",
    label: "Itens ativos",
  },
  {
    description: "Prescrições em vigor vinculadas aos pacientes.",
    icon: ClipboardList,
    key: "active_prescriptions",
    label: "Prescrições ativas",
  },
  {
    description: "Alertas internos pendentes de resolucao.",
    icon: AlertTriangle,
    key: "open_alerts",
    label: "Alertas abertos",
  },
  {
    description: "Itens que já estao abaixo do estoque minimo.",
    icon: TriangleAlert,
    key: "low_stock_items",
    label: "Estoque baixo",
  },
] as const

const calculationCards = [
  {
    description: "Itens com menos de sete dias restantes ou em condição crítica.",
    icon: TriangleAlert,
    key: "items_at_risk",
    label: "Menos de 7 dias",
  },
  {
    description: "Itens com cobertura crítica e necessidade de atenção imediata.",
    icon: AlertTriangle,
    key: "critical_items",
    label: "Itens críticos",
  },
  {
    description: "Casos em que o consumo realizado esta acima ou abaixo do esperado.",
    icon: ClipboardList,
    key: "relevant_divergences",
    label: "Divergencias",
  },
  {
    description: "Pacientes com pelo menos um item exigindo acompanhamento prioritario.",
    icon: Users,
    key: "patients_at_risk",
    label: "Pacientes com risco",
  },
] as const

const workflowSteps = [
  {
    description: "Prepare as unidades base para itens e prescrições.",
    label: "Unidades",
    to: "/units",
  },
  {
    description: "Cadastre medicamentos e insumos antes de prescrever.",
    label: "Itens",
    to: "/items",
  },
  {
    description: "Cadastre e acompanhe pacientes ativos do sistema.",
    label: "Pacientes",
    to: "/patients",
  },
  {
    description: "Vincule pacientes e itens nas prescrições ativas.",
    label: "Prescrições",
    to: "/prescriptions",
  },
  {
    description: "Lance movimentacoes e consulte saldo por item.",
    label: "Estoque",
    to: "/inventory",
  },
  {
    description: "Acompanhe e resolva alertas internos persistidos.",
    label: "Alertas",
    to: "/alerts",
  },
] as const

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível carregar o resumo do dashboard."
}

function getSystemStatus(summary: DashboardSummary | null) {
  if (!summary) {
    return {
      description: "Carregue os dados para ver a situação inicial do sistema.",
      label: "Aguardando resumo",
      variant: "outline" as const,
    }
  }

  if (
    summary.calculation.critical_items > 0 ||
    summary.open_alerts > 0 ||
    summary.low_stock_items > 0
  ) {
    return {
      description: "Existem itens críticos, alertas abertos ou necessidade de reposicao que merecem atenção.",
      label: "Atenção operacional",
      variant: "warning" as const,
    }
  }

  if (
    summary.calculation.relevant_divergences > 0 ||
    summary.calculation.items_at_risk > 0
  ) {
    return {
      description: "O sistema esta estavel, mas ha sinais de consumo que merecem acompanhamento.",
      label: "Acompanhamento recomendado",
      variant: "outline" as const,
    }
  }

  return {
    description: "Não ha alertas abertos, itens críticos nem divergencias relevantes no resumo atual.",
    label: "Situação estavel",
    variant: "success" as const,
  }
}

function getRiskScoreVariant(riskScore: number) {
  if (riskScore >= 5) {
    return "danger" as const
  }

  if (riskScore >= 3) {
    return "warning" as const
  }

  return "outline" as const
}

function getCalculationStatus(summary: DashboardCalculationSummary | null) {
  if (!summary) {
    return {
      description: "Carregue o painel para visualizar o resumo operacional calculado pelo sistema.",
      label: "Aguardando cálculo",
      variant: "outline" as const,
    }
  }

  if (summary.critical_items > 0) {
    return {
      description: "Há itens em condição crítica e com necessidade de atenção imediata.",
      label: "Risco elevado",
      variant: "danger" as const,
    }
  }

  if (summary.items_at_risk > 0 || summary.relevant_divergences > 0) {
    return {
      description: "O motor identificou cobertura curta ou diferenças relevantes entre o previsto e o realizado.",
      label: "Acompanhamento recomendado",
      variant: "warning" as const,
    }
  }

  return {
    description: "Não há sinais operacionais relevantes no resumo atual do motor de cálculo.",
    label: "Situação estável",
    variant: "success" as const,
  }
}

export function DashboardPage() {
  const { token, user } = useAuth()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [alertsSummary, setAlertsSummary] = useState<AlertSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [divergenceCandidates, setDivergenceCandidates] = useState<CalculationAlertCandidate[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const loadDashboard = useCallback(async () => {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      setSummary(null)
      setOverview(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const [summaryResponse, overviewResponse, divergencesResponse, alertsSummaryResponse] = await Promise.all([
        getDashboardSummary(token),
        getDashboardOverview(token),
        getRelevantDivergenceCandidatesFromCalculation(token, {
          limit: 20,
        }),
        getAlertsSummaryWithFallback(token, { status: "open" }),
      ])

      setSummary(summaryResponse.data)
      setOverview(overviewResponse.data)
      setDivergenceCandidates(divergencesResponse.data)
      setAlertsSummary(alertsSummaryResponse.data)
    } catch (requestError) {
      setSummary(null)
      setOverview(null)
      setDivergenceCandidates([])
      setAlertsSummary(null)
      setError(getErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [token])

  useEffect(() => {
    void loadDashboard()
  }, [loadDashboard])

  const systemStatus = getSystemStatus(summary)
  const calculationSummary: DashboardCalculationSummary | null =
    overview?.calculation ?? summary?.calculation ?? null
  const calculationStatus = getCalculationStatus(calculationSummary)

  return (
    <div className="grid gap-6">
      <section className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
        <Card className="overflow-hidden border-0 bg-[linear-gradient(135deg,rgba(10,75,63,0.96),rgba(14,110,94,0.96))] text-white shadow-soft">
          <CardHeader>
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <Badge className="border-white/20 bg-white/10 text-white" variant="outline">
                Visão geral
              </Badge>
              <Badge className="border-white/20 bg-white/10 text-white" variant="outline">
                Resumo do sistema
              </Badge>
            </div>
            <CardTitle className="text-3xl font-semibold leading-tight">
              Acompanhe rapidamente a situação geral da casa assistencial.
            </CardTitle>
            <CardDescription className="max-w-2xl text-base text-emerald-50/85">
              Veja os principais indicadores do dia, acompanhe o consumo previsto e identifique o que precisa de atenção.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card className="bg-white/92">
          <CardHeader>
            <CardTitle>Situação do sistema</CardTitle>
            <CardDescription>Resumo rapido para orientar o acompanhamento diario.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
              <div className="mb-3 inline-flex rounded-full bg-background p-2 text-primary">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium">{systemStatus.label}</p>
                <Badge variant={systemStatus.variant}>{isLoading ? "carregando" : "resumo ativo"}</Badge>
              </div>
              <p className="mt-2 text-muted-foreground">{systemStatus.description}</p>
            </div>

            <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
              <p className="text-muted-foreground">Usuario autenticado</p>
              <p className="font-medium">{user?.full_name}</p>
              <p className="text-muted-foreground">{user?.email}</p>
            </div>

            <Button className="w-full justify-between" disabled={isLoading} onClick={() => void loadDashboard()} variant="outline">
              Atualizar resumo
              <RefreshCcw className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </section>

      {error ? (
        <FeedbackBanner
          message={error}
          title="Falha ao carregar o dashboard"
          variant="error"
        />
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {summaryCards.map(({ description, icon: Icon, key, label }) => (
          <Card className="bg-white/92" key={key}>
            <CardHeader className="space-y-4">
              <div className="inline-flex w-fit rounded-full bg-secondary p-2 text-primary">
                <Icon className="h-4 w-4" />
              </div>
              <div>
                <CardDescription>{label}</CardDescription>
                <CardTitle className="mt-2 text-3xl font-semibold">
                  {isLoading ? "..." : summary ? summary[key] : "--"}
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">{description}</CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="bg-white/92">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Alertas críticos abertos</p>
            <p className="mt-2 text-3xl font-semibold">
              {isLoading ? "..." : alertsSummary?.open_critical ?? "--"}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-white/92">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Alertas de aviso abertos</p>
            <p className="mt-2 text-3xl font-semibold">
              {isLoading ? "..." : alertsSummary?.open_warning ?? "--"}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-white/92">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Pacientes com alerta aberto</p>
            <p className="mt-2 text-3xl font-semibold">
              {isLoading ? "..." : alertsSummary?.patients_with_open_alerts ?? "--"}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-white/92">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Itens com alerta aberto</p>
            <p className="mt-2 text-3xl font-semibold">
              {isLoading ? "..." : alertsSummary?.items_with_open_alerts ?? "--"}
            </p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4">
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
            Motor de cálculo
          </p>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Risco operacional do sistema</h2>
              <p className="text-sm text-muted-foreground">
                Use estes indicadores para acompanhar cobertura, criticidade e divergências de consumo.
              </p>
            </div>
            <Badge variant={calculationStatus.variant}>
              {isLoading ? "carregando" : calculationStatus.label}
            </Badge>
          </div>
        </div>

        <Card className="bg-white/92">
          <CardContent className="grid gap-4 p-6 xl:grid-cols-[0.9fr_1.1fr]">
            <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4">
              <div className="mb-3 inline-flex rounded-full bg-background p-2 text-primary">
                <Activity className="h-4 w-4" />
              </div>
              <p className="font-medium">{calculationStatus.label}</p>
              <p className="mt-2 text-sm text-muted-foreground">{calculationStatus.description}</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {calculationCards.map(({ description, icon: Icon, key, label }) => (
                <Card className="bg-background/70 shadow-none" key={key}>
                  <CardHeader className="space-y-4">
                    <div className="inline-flex w-fit rounded-full bg-secondary p-2 text-primary">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <CardDescription>{label}</CardDescription>
                      <CardTitle className="mt-2 text-3xl font-semibold">
                        {isLoading ? "..." : calculationSummary ? calculationSummary[key] : "--"}
                      </CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">{description}</CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4">
        <Card className="bg-white/92">
          <CardHeader>
            <CardTitle>Leitura dos status do motor</CardTitle>
            <CardDescription>
              Os mesmos status aparecem nas telas de pacientes, itens e nas análises operacionais.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CalculationStatusLegend />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4">
        <CalculationDivergenceList candidates={divergenceCandidates} isLoading={isLoading} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1.1fr]">
        <Card className="bg-white/92">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-primary" />
              Pacientes com maior risco operacional
            </CardTitle>
            <CardDescription>
              Priorize primeiro quem concentra mais itens em atencão, criticidade ou divergencias.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoading ? (
              <div className="rounded-2xl border border-border/70 bg-secondary/25 px-4 py-10 text-sm text-muted-foreground">
                Carregando prioridades operacionais...
              </div>
            ) : overview?.risk_patients.length ? (
              overview.risk_patients.map((riskPatient) => (
                <div className="rounded-2xl border border-border/70 bg-secondary/35 p-4" key={riskPatient.patient_id}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{riskPatient.patient_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {riskPatient.items_requiring_attention} itens exigem acompanhamento neste momento.
                      </p>
                    </div>
                    <Badge variant={getRiskScoreVariant(riskPatient.risk_score)}>
                      Risco {riskPatient.risk_score}
                    </Badge>
                  </div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <div>
                      <p className="text-xs text-muted-foreground">Itens em atenção</p>
                      <p className="font-medium">{riskPatient.items_requiring_attention}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Itens críticos</p>
                      <p className="font-medium">{riskPatient.critical_items}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Divergencias</p>
                      <p className="font-medium">{riskPatient.relevant_divergences}</p>
                    </div>
                  </div>
                  <div className="mt-4">
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/patients/${riskPatient.patient_id}`}>Ver paciente</Link>
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
                <EmptyState
                  description="Quando o motor identificar pacientes com itens em atenção, a prioridade aparecerá aqui."
                  icon={Users}
                  title="Nenhum paciente em risco"
                />
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-white/92">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-4 w-4 text-primary" />
              Caminho sugerido
            </CardTitle>
            <CardDescription>
              Sequencia recomendada para organizar o uso do sistema.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 lg:grid-cols-2">
            {workflowSteps.map((step, index) => (
              <div className="rounded-2xl border border-border/70 bg-secondary/25 p-4" key={step.to}>
                <p className="text-sm text-muted-foreground">Passo {index + 1}</p>
                <p className="mt-1 font-medium">{step.label}</p>
                <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
                <Button asChild className="mt-4" size="sm" variant="outline">
                  <Link to={step.to}>Abrir modulo</Link>
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
