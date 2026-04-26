import type { CalculationStatus } from "@/types/calculation"

import { CalculationStatusBadge } from "@/components/app/calculation-status-badge"
import { getCalculationStatusMeta } from "@/features/calculation/calculation-status"

const defaultStatuses: CalculationStatus[] = [
  "ok",
  "low_stock",
  "critical_stock",
  "consumption_above_expected",
  "consumption_below_expected",
  "inconsistent_data",
  "invalid_prescription",
]

type CalculationStatusLegendProps = {
  statuses?: CalculationStatus[]
}

export function CalculationStatusLegend({
  statuses = defaultStatuses,
}: CalculationStatusLegendProps) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {statuses.map((status) => {
        const meta = getCalculationStatusMeta(status)

        return (
          <div
            className="rounded-2xl border border-border/70 bg-secondary/25 p-4"
            key={status}
          >
            <CalculationStatusBadge status={status} />
            <p className="mt-3 text-sm text-muted-foreground">{meta.description}</p>
          </div>
        )
      })}
    </div>
  )
}
