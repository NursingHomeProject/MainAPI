import { BellRing } from "lucide-react"
import { Link } from "react-router-dom"

import { EmptyState } from "@/components/app/empty-state"
import { CalculationStatusBadge } from "@/components/app/calculation-status-badge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { getCalculationStatusMeta } from "@/features/calculation/calculation-status"
import {
  formatExpectedRange,
  getComparisonWindowLabel,
  getUsageModeLabel,
} from "@/features/prescriptions/prescription-presentation"
import { formatOperationalTextNumbers } from "@/lib/utils"
import type { CalculationAlertCandidate } from "@/types/calculation"

type CalculationAlertCandidatesListProps = {
  candidates: CalculationAlertCandidate[]
  isLoading?: boolean
}

export function CalculationAlertCandidatesList({
  candidates,
  isLoading = false,
}: CalculationAlertCandidatesListProps) {
  return (
    <Card className="bg-white/92">
      <CardHeader>
        <CardTitle>Candidatos a alerta do motor</CardTitle>
        <CardDescription>
          Estes casos foram identificados pelo motor de cálculo e merecem acompanhamento.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {isLoading ? (
          <div className="rounded-2xl border border-border/70 bg-secondary/25 px-4 py-10 text-muted-foreground">
            Carregando candidatos do motor...
          </div>
        ) : candidates.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border/80 bg-secondary/25 px-4">
            <EmptyState
              description="Quando o motor identificar risco operacional, os candidatos aparecerão aqui."
              icon={BellRing}
              title="Nenhum candidato a alerta"
            />
          </div>
        ) : (
          <>
            <div className="rounded-2xl border border-border/70 bg-secondary/20 px-4 py-3 text-sm text-muted-foreground">
              {candidates.length} caso(s) sinalizados pelo motor para acompanhamento.
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
                    <Badge variant={candidate.should_alert ? "warning" : "outline"}>
                      {candidate.should_alert ? "Requer atenção" : "Sem alerta"}
                    </Badge>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <div>
                    <p className="text-muted-foreground">Paciente</p>
                    <p className="font-medium text-foreground">
                      {candidate.patient_name || candidate.patient_id}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Item</p>
                    <p className="font-medium text-foreground">{candidate.item_name}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Situação do motor</p>
                    <p className="font-medium text-foreground">
                      {getCalculationStatusMeta(candidate.status).label}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Requer atenção</p>
                    <p className="font-medium text-foreground">
                      {candidate.should_alert ? "Sim" : "Não"}
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

                <div className="mt-4 rounded-2xl border border-border/70 bg-background/70 p-4">
                  <p className="text-muted-foreground">Motivo do alerta</p>
                  <p className="mt-2 font-medium text-foreground">
                    {formatOperationalTextNumbers(
                      candidate.alert_reason || "Sem motivo adicional informado pelo motor.",
                    )}
                  </p>
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
