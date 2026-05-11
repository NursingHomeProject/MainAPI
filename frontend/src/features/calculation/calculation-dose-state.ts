import type {
  CalculationAdministrationDayStatus,
  CalculationDoseOccurrenceState,
} from "@/types/calculation"

type DoseStateMeta = {
  description: string
  label: string
  variant: "success" | "warning" | "danger" | "outline"
}

const calculationDoseStateMeta: Record<
  CalculationDoseOccurrenceState,
  DoseStateMeta
> = {
  completed: {
    description: "A dose já foi registrada para o horário previsto.",
    label: "Concluída",
    variant: "success",
  },
  due_now: {
    description: "A dose está na janela de administração e ainda dentro da tolerância.",
    label: "Na janela",
    variant: "warning",
  },
  not_due_yet: {
    description: "O horário previsto da dose ainda não chegou.",
    label: "Ainda não chegou",
    variant: "outline",
  },
  overdue: {
    description: "O horário da dose e a tolerância já passaram sem registro de administração.",
    label: "Atrasada",
    variant: "danger",
  },
}

const administrationDayStatusMeta: Record<
  CalculationAdministrationDayStatus,
  DoseStateMeta
> = {
  completed: {
    description: "Todas as doses previstas do dia já foram registradas.",
    label: "Dia concluído",
    variant: "success",
  },
  due_now: {
    description: "Existe dose na janela de administração neste momento.",
    label: "Dose na janela",
    variant: "warning",
  },
  invalid_schedule: {
    description: "A agenda do dia não pôde ser montada com segurança.",
    label: "Agenda inválida",
    variant: "danger",
  },
  missed_dose: {
    description: "Existe dose atrasada sem registro de administração.",
    label: "Dose atrasada",
    variant: "danger",
  },
  not_due_yet: {
    description: "Ainda não existe dose vencida ou em janela de administração.",
    label: "Sem dose vencida",
    variant: "outline",
  },
  overdue: {
    description: "Existe dose atrasada para o dia atual.",
    label: "Atraso no dia",
    variant: "danger",
  },
  partially_completed_day: {
    description: "Parte das doses do dia já foi concluída e ainda há horários futuros.",
    label: "Dia em andamento",
    variant: "warning",
  },
}

export function getCalculationDoseStateMeta(
  state: CalculationDoseOccurrenceState,
) {
  return calculationDoseStateMeta[state]
}

export function getAdministrationDayStatusMeta(
  status: CalculationAdministrationDayStatus,
) {
  return administrationDayStatusMeta[status]
}
