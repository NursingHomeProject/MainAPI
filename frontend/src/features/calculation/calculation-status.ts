import type { CalculationStatus } from "@/types/calculation"

export type CalculationStatusMeta = {
  description: string
  label: string
  variant: "success" | "warning" | "danger" | "outline"
}

const calculationStatusMeta: Record<CalculationStatus, CalculationStatusMeta> = {
  consumption_above_expected: {
    description: "O consumo realizado está acima do esperado e merece acompanhamento.",
    label: "Consumo acima do esperado",
    variant: "warning",
  },
  consumption_below_expected: {
    description: "O consumo realizado está abaixo do esperado e merece revisão.",
    label: "Consumo abaixo do esperado",
    variant: "warning",
  },
  critical_stock: {
    description: "O item está em condição crítica e requer atenção imediata.",
    label: "Estoque crítico",
    variant: "danger",
  },
  inconsistent_data: {
    description: "Os dados atuais não são consistentes para acompanhamento seguro.",
    label: "Dados inconsistentes",
    variant: "danger",
  },
  invalid_prescription: {
    description: "A prescrição atual não permite cálculo confiável do consumo.",
    label: "Prescrição inválida",
    variant: "danger",
  },
  low_stock: {
    description: "O item tem cobertura curta e precisa de acompanhamento.",
    label: "Estoque baixo",
    variant: "warning",
  },
  ok: {
    description: "A situação está dentro do esperado para este momento.",
    label: "Dentro do esperado",
    variant: "success",
  },
}

export function getCalculationStatusMeta(status: CalculationStatus) {
  return calculationStatusMeta[status]
}
