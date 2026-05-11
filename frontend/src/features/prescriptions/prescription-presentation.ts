import type {
  PrescriptionComparisonWindow,
  PrescriptionUsageMode,
} from "@/types/prescription"

export const prescriptionUsageModeOptions: Array<{
  value: PrescriptionUsageMode
  label: string
  description: string
}> = [
  {
    value: "fixed",
    label: "Uso fixo",
    description: "Compara a rotina prevista por horario ou pelo total do dia.",
  },
  {
    value: "variable",
    label: "Uso variavel",
    description: "Compara o consumo dentro de uma faixa operacional esperada.",
  },
  {
    value: "on_demand",
    label: "Sob demanda",
    description: "Monitora uso real e estoque sem cobrar aderencia de rotina.",
  },
]

export const fixedComparisonWindowOptions: Array<{
  value: PrescriptionComparisonWindow
  label: string
  description: string
}> = [
  {
    value: "scheduled_times",
    label: "Horarios prescritos",
    description: "Considera apenas os horarios que já deveriam ter acontecido.",
  },
  {
    value: "daily_total",
    label: "Total do dia",
    description: "Compara o total previsto no dia sem depender de horario rigido.",
  },
]

export const operationalComparisonWindowOptions: Array<{
  value: PrescriptionComparisonWindow
  label: string
  description: string
}> = [
  {
    value: "daily_total",
    label: "Total do dia",
    description: "Compara o total consumido no dia corrente.",
  },
  {
    value: "shift_window",
    label: "Janela de turno",
    description: "Compara o consumo dentro do turno operacional atual.",
  },
  {
    value: "rolling_24h",
    label: "Ultimas 24h",
    description: "Compara a janela movel das ultimas 24 horas.",
  },
]

export function getUsageModeLabel(usageMode: PrescriptionUsageMode | null | undefined) {
  switch (usageMode) {
    case "fixed":
      return "Uso fixo"
    case "variable":
      return "Uso variavel"
    case "on_demand":
      return "Sob demanda"
    default:
      return "Não informado"
  }
}

export function getUsageModeDescription(
  usageMode: PrescriptionUsageMode | null | undefined,
) {
  return (
    prescriptionUsageModeOptions.find((option) => option.value === usageMode)
      ?.description ?? "Modo de uso não informado."
  )
}

export function getComparisonWindowLabel(
  comparisonWindow: PrescriptionComparisonWindow | null | undefined,
) {
  switch (comparisonWindow) {
    case "scheduled_times":
      return "Horarios prescritos"
    case "daily_total":
      return "Total do dia"
    case "shift_window":
      return "Janela de turno"
    case "rolling_24h":
      return "Ultimas 24h"
    default:
      return "Não informada"
  }
}

export function getComparisonWindowDescription(
  comparisonWindow: PrescriptionComparisonWindow | null | undefined,
) {
  const option = [...fixedComparisonWindowOptions, ...operationalComparisonWindowOptions].find(
    (item) => item.value === comparisonWindow,
  )

  return option?.description ?? "Janela de comparação não informada."
}

export function getComparisonWindowOptions(usageMode: PrescriptionUsageMode) {
  if (usageMode === "fixed") {
    return fixedComparisonWindowOptions
  }

  return operationalComparisonWindowOptions
}

export function getDefaultComparisonWindowForUsageMode(
  usageMode: PrescriptionUsageMode,
): PrescriptionComparisonWindow {
  if (usageMode === "fixed") {
    return "scheduled_times"
  }

  return "rolling_24h"
}

export function formatExpectedRange(
  minExpectedPerDay: string | null | undefined,
  maxExpectedPerDay: string | null | undefined,
  unitSymbol?: string | null,
) {
  if (!minExpectedPerDay && !maxExpectedPerDay) {
    return "Não configurada"
  }

  const suffix = unitSymbol ? ` ${unitSymbol}` : ""

  if (minExpectedPerDay && maxExpectedPerDay) {
    if (minExpectedPerDay === maxExpectedPerDay) {
      return `${minExpectedPerDay}${suffix} por dia`
    }

    return `${minExpectedPerDay} a ${maxExpectedPerDay}${suffix} por dia`
  }

  if (minExpectedPerDay) {
    return `Minimo ${minExpectedPerDay}${suffix} por dia`
  }

  return `Maximo ${maxExpectedPerDay}${suffix} por dia`
}
