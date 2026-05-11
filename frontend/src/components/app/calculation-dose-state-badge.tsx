import { Badge } from "@/components/ui/badge"
import { getCalculationDoseStateMeta } from "@/features/calculation/calculation-dose-state"
import type { CalculationDoseOccurrenceState } from "@/types/calculation"

type CalculationDoseStateBadgeProps = {
  state: CalculationDoseOccurrenceState
}

export function CalculationDoseStateBadge({
  state,
}: CalculationDoseStateBadgeProps) {
  const meta = getCalculationDoseStateMeta(state)

  return <Badge variant={meta.variant}>{meta.label}</Badge>
}
