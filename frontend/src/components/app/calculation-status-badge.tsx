import { Badge } from "@/components/ui/badge"
import { getCalculationStatusMeta } from "@/features/calculation/calculation-status"
import type { CalculationStatus } from "@/types/calculation"

type CalculationStatusBadgeProps = {
  status: CalculationStatus
}

export function CalculationStatusBadge({ status }: CalculationStatusBadgeProps) {
  const meta = getCalculationStatusMeta(status)

  return <Badge variant={meta.variant}>{meta.label}</Badge>
}
