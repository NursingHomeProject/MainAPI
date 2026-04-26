import { Link } from "react-router-dom"

import { EmptyState } from "@/components/app/empty-state"
import { CalculationStatusBadge } from "@/components/app/calculation-status-badge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  formatExpectedRange,
  getComparisonWindowLabel,
  getUsageModeLabel,
} from "@/features/prescriptions/prescription-presentation"
import { formatDecimalAsInteger, formatSignedDecimalAsInteger } from "@/lib/utils"
import type { CalculationAlertCandidate } from "@/types/calculation"
import { ClipboardList } from "lucide-react"

function getDivergenceLabel(divergenceStatus: CalculationAlertCandidate["divergence_status"]) {
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

function getDivergenceVariant(divergenceStatus: CalculationAlertCandidate["divergence_status"]) {
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

function formatMetric(value: string | null, unitSymbol?: string | null) {
  if (!value) {
    return "Não disponível"
  }

  const formatted = formatDecimalAsInteger(value)
  return unitSymbol ? `${formatted} ${unitSymbol}` : formatted
}

type CalculationDivergenceListProps = {
  candidates: CalculationAlertCandidate[]
  isLoading?: boolean
}

export function CalculationDivergenceList({
  candidates,
  isLoading = false,
}: CalculationDivergenceListProps) {
  return (
    <Card className="bg-white/92">
      <CardHeader>
        <CardTitle>Divergências detectadas</CardTitle>
        <CardDescription>
          Compare o previsto e o realizado para identificar rapidamente onde o acompanhamento precisa de revisão.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {isLoading ? (
          <div className="rounded-2xl border border-border/70 bg-secondary/25 px-4 py-10 text-muted-foreground">
            Carregando divergências...
          </div>
        ) : candidates.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
            <EmptyState
              description="Quando houver diferença relevante entre o previsto e o realizado, os casos aparecerão aqui."
              icon={ClipboardList}
              title="Nenhuma divergência relevante"
            />
          </div>
        ) : (
          <>
            <div className="rounded-2xl border border-border/70 bg-secondary/20 px-4 py-3 text-sm text-muted-foreground">
              {candidates.length} caso(s) com diferença relevante entre o previsto e o realizado.
            </div>
            {candidates.map((candidate) => (
              <div
                className="rounded-2xl border border-border/70 bg-secondary/35 p-4"
                key={`${candidate.patient_id}-${candidate.item_id}`}
              >
                <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{candidate.patient_name || "Paciente não identificado"}</p>
                    <p className="text-muted-foreground">{candidate.item_name}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <CalculationStatusBadge status={candidate.status} />
                    <Badge variant={getDivergenceVariant(candidate.divergence_status)}>
                      {getDivergenceLabel(candidate.divergence_status)}
                    </Badge>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <div>
                    <p className="text-muted-foreground">Esperado até agora</p>
                    <p className="font-medium text-foreground">
                      {formatMetric(
                        candidate.expected_consumption_until_now,
                        candidate.unit_symbol,
                      )}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Realizado até agora</p>
                    <p className="font-medium text-foreground">
                      {formatMetric(
                        candidate.actual_consumption_until_now,
                        candidate.unit_symbol,
                      )}
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
                    <p className="text-muted-foreground">Acompanhamento</p>
                    <p className="font-medium text-foreground">
                      {candidate.alert_reason || "Sem observações adicionais."}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Tipo de uso</p>
                    <p className="font-medium text-foreground">
                      {getUsageModeLabel(candidate.usage_mode)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Comparação</p>
                    <p className="font-medium text-foreground">
                      {getComparisonWindowLabel(candidate.comparison_window)}
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

                <div className="mt-4 flex flex-wrap gap-2">
                  <Button asChild size="sm" variant="outline">
                    <Link to={`/patients/${candidate.patient_id}`}>Ver paciente</Link>
                  </Button>
                  <Button asChild size="sm" variant="outline">
                    <Link to={`/items/${candidate.item_id}`}>Ver item</Link>
                  </Button>
                </div>
              </div>
            ))}
          </>
        )}
      </CardContent>
    </Card>
  )
}
