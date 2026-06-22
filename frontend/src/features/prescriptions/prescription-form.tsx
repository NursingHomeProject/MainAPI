import { type FormEvent, useState } from "react"
import { Link } from "react-router-dom"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { NativeSelect } from "@/components/app/native-select"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  getComparisonWindowOptions,
  getDefaultComparisonWindowForUsageMode,
  getUsageModeDescription,
  prescriptionUsageModeOptions,
} from "@/features/prescriptions/prescription-presentation"
import type { Item } from "@/types/item"
import type { Patient } from "@/types/patient"
import type {
  PrescriptionComparisonWindow,
  PrescriptionCreatePayload,
  PrescriptionUsageMode,
} from "@/types/prescription"

export type PrescriptionFormValues = PrescriptionCreatePayload

type PrescriptionFormProps = {
  defaultValues?: PrescriptionFormValues
  description: string
  error: string | null
  isSubmitting: boolean
  items: Item[]
  itemsError: string | null
  itemsLoading: boolean
  patients: Patient[]
  patientsError: string | null
  patientsLoading: boolean
  submitLabel: string
  title: string
  onCancel: () => void
  onSubmit: (values: PrescriptionFormValues) => Promise<void>
}

const defaultPrescriptionValues: PrescriptionFormValues = {
  patient_id: "",
  item_id: "",
  dose_amount: "1",
  frequency_per_day: 1,
  specific_times: null,
  usage_mode: "fixed",
  comparison_window: "scheduled_times",
  min_expected_per_day: null,
  max_expected_per_day: null,
  start_date: "",
  end_date: null,
  is_active: true,
}

function shouldShowSpecificTimes(usageMode: PrescriptionUsageMode) {
  return usageMode === "fixed"
}

function shouldShowExpectedRange(usageMode: PrescriptionUsageMode) {
  return usageMode === "variable" || usageMode === "on_demand"
}

export function PrescriptionForm({
  defaultValues,
  description,
  error,
  isSubmitting,
  items,
  itemsError,
  itemsLoading,
  onCancel,
  onSubmit,
  patients,
  patientsError,
  patientsLoading,
  submitLabel,
  title,
}: PrescriptionFormProps) {
  const [values, setValues] = useState<PrescriptionFormValues>(defaultValues ?? defaultPrescriptionValues)
  // Lista de horários como array de strings "HH:MM" — um input por posição
  const [specificTimesList, setSpecificTimesList] = useState<string[]>(
    defaultValues?.specific_times ?? [],
  )

  const comparisonWindowOptions = getComparisonWindowOptions(values.usage_mode)

  const availablePatients = patients.filter((patient) => patient.is_active || patient.id === values.patient_id)
  const availableItems = items.filter((item) => item.is_active || item.id === values.item_id)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    await onSubmit({
      patient_id: values.patient_id,
      item_id: values.item_id,
      dose_amount: values.dose_amount,
      frequency_per_day: values.frequency_per_day,
      specific_times: shouldShowSpecificTimes(values.usage_mode)
        ? (() => {
            // Envia apenas os horários preenchidos, na quantidade da frequência
            const filled = specificTimesList
              .slice(0, values.frequency_per_day)
              .filter(Boolean)
            return filled.length > 0 ? filled : null
          })()
        : null,
      usage_mode: values.usage_mode,
      comparison_window: values.comparison_window,
      min_expected_per_day: shouldShowExpectedRange(values.usage_mode)
        ? values.min_expected_per_day?.trim() || null
        : null,
      max_expected_per_day: shouldShowExpectedRange(values.usage_mode)
        ? values.max_expected_per_day?.trim() || null
        : null,
      start_date: values.start_date,
      end_date: values.end_date?.trim() ? values.end_date : null,
      is_active: values.is_active,
    })
  }

  function handleUsageModeChange(nextUsageMode: PrescriptionUsageMode) {
    const nextComparisonWindow = getComparisonWindowOptions(nextUsageMode).some(
      (option) => option.value === values.comparison_window,
    )
      ? values.comparison_window
      : getDefaultComparisonWindowForUsageMode(nextUsageMode)

    setValues((current) => ({
      ...current,
      usage_mode: nextUsageMode,
      comparison_window: nextComparisonWindow,
      min_expected_per_day:
        nextUsageMode === "fixed" ? null : current.min_expected_per_day,
      max_expected_per_day:
        nextUsageMode === "fixed" ? null : current.max_expected_per_day,
    }))

    if (nextUsageMode !== "fixed") {
      setSpecificTimesList([])
    }
  }

  function handleComparisonWindowChange(nextComparisonWindow: PrescriptionComparisonWindow) {
    setValues((current) => ({
      ...current,
      comparison_window: nextComparisonWindow,
    }))
  }

  const dependenciesLoading = patientsLoading || itemsLoading
  const dependenciesError = patientsError || itemsError
  const hasDependencies = availablePatients.length > 0 && availableItems.length > 0

  return (
    <Card className="bg-white/92">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {dependenciesLoading ? (
          <div className="rounded-2xl border border-border/80 bg-secondary/20 px-4 py-6 text-sm text-muted-foreground">
            Carregando pacientes e itens...
          </div>
        ) : dependenciesError ? (
          <FeedbackBanner message={dependenciesError} variant="error" />
        ) : !hasDependencies ? (
          <FeedbackBanner
            message={
              <>
                Para criar prescrições, cadastre pelo menos um paciente e um item ativos. Use{" "}
                <Link className="font-medium underline" to="/patients/new">
                  /patients/new
                </Link>{" "}
                e{" "}
                <Link className="font-medium underline" to="/items/new">
                  /items/new
                </Link>
                .
              </>
            }
            variant="warning"
          />
        ) : (
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="grid gap-5 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="patient_id">Paciente</Label>
                <NativeSelect
                  id="patient_id"
                  onChange={(event) => setValues((current) => ({ ...current, patient_id: event.target.value }))}
                  required
                  value={values.patient_id}
                >
                  <option value="">Selecione um paciente</option>
                  {availablePatients.map((patient) => (
                    <option key={patient.id} value={patient.id}>
                      {patient.full_name}
                      {patient.is_active ? "" : " - inativo"}
                    </option>
                  ))}
                </NativeSelect>
              </div>

              <div className="space-y-2">
                <Label htmlFor="item_id">Item</Label>
                <NativeSelect
                  id="item_id"
                  onChange={(event) => setValues((current) => ({ ...current, item_id: event.target.value }))}
                  required
                  value={values.item_id}
                >
                  <option value="">Selecione um item</option>
                  {availableItems.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                      {item.is_active ? "" : " - inativo"}
                    </option>
                  ))}
                </NativeSelect>
              </div>

              <div className="space-y-2">
                <Label htmlFor="dose_amount">Dose</Label>
                <Input
                  id="dose_amount"
                  inputMode="decimal"
                  onChange={(event) => setValues((current) => ({ ...current, dose_amount: event.target.value }))}
                  placeholder="1"
                  required
                  value={values.dose_amount}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="frequency_per_day">Frequencia por dia</Label>
                <Input
                  id="frequency_per_day"
                  inputMode="numeric"
                  min="1"
                  onChange={(event) => {
                    const newFreq = Math.max(1, Number(event.target.value || 1))
                    setValues((current) => ({
                      ...current,
                      frequency_per_day: newFreq,
                    }))
                    // Sincroniza o número de inputs de horário com a nova frequência
                    if (shouldShowSpecificTimes(values.usage_mode)) {
                      setSpecificTimesList((current) => {
                        if (newFreq > current.length) {
                          // Adiciona slots vazios para os novos horários
                          return [...current, ...Array<string>(newFreq - current.length).fill("")]
                        }
                        // Remove os slots excedentes
                        return current.slice(0, newFreq)
                      })
                    }
                  }}
                  placeholder="1"
                  required
                  type="number"
                  value={values.frequency_per_day}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="usage_mode">Tipo de uso</Label>
                <NativeSelect
                  id="usage_mode"
                  onChange={(event) =>
                    handleUsageModeChange(event.target.value as PrescriptionUsageMode)
                  }
                  value={values.usage_mode}
                >
                  {prescriptionUsageModeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </NativeSelect>
                <p className="text-xs text-muted-foreground">
                  {getUsageModeDescription(values.usage_mode)}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="comparison_window">Lógica de comparação</Label>
                <NativeSelect
                  id="comparison_window"
                  onChange={(event) =>
                    handleComparisonWindowChange(
                      event.target.value as PrescriptionComparisonWindow,
                    )
                  }
                  value={values.comparison_window}
                >
                  {comparisonWindowOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </NativeSelect>
                <p className="text-xs text-muted-foreground">
                  {comparisonWindowOptions.find(
                    (option) => option.value === values.comparison_window,
                  )?.description ?? "Escolha como o motor deve comparar o consumo."}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="start_date">Data inicial</Label>
                <Input
                  id="start_date"
                  onChange={(event) => setValues((current) => ({ ...current, start_date: event.target.value }))}
                  required
                  type="date"
                  value={values.start_date}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="end_date">Data final</Label>
                <Input
                  id="end_date"
                  onChange={(event) => setValues((current) => ({ ...current, end_date: event.target.value || null }))}
                  type="date"
                  value={values.end_date ?? ""}
                />
              </div>
            </div>

            {shouldShowSpecificTimes(values.usage_mode) ? (
              <div className="space-y-3">
                <div>
                  <Label>Horários específicos</Label>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Um campo por dose diária. Deixe em branco para usar apenas a frequência como base.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {Array.from({ length: Math.max(values.frequency_per_day, 1) }, (_, index) => (
                    <div className="space-y-1" key={index}>
                      <p className="text-xs font-medium text-muted-foreground">
                        {index + 1}ª dose
                      </p>
                      <Input
                        id={`specific_time_${index}`}
                        onChange={(e) => {
                          const next = [...specificTimesList]
                          next[index] = e.target.value
                          setSpecificTimesList(next)
                        }}
                        type="time"
                        value={specificTimesList[index] ?? ""}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {shouldShowExpectedRange(values.usage_mode) ? (
              <div className="grid gap-5 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="min_expected_per_day">Minimo esperado por dia</Label>
                  <Input
                    id="min_expected_per_day"
                    inputMode="decimal"
                    onChange={(event) =>
                      setValues((current) => ({
                        ...current,
                        min_expected_per_day: event.target.value || null,
                      }))
                    }
                    placeholder="Ex.: 3"
                    value={values.min_expected_per_day ?? ""}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max_expected_per_day">Maximo esperado por dia</Label>
                  <Input
                    id="max_expected_per_day"
                    inputMode="decimal"
                    onChange={(event) =>
                      setValues((current) => ({
                        ...current,
                        max_expected_per_day: event.target.value || null,
                      }))
                    }
                    placeholder="Ex.: 5"
                    value={values.max_expected_per_day ?? ""}
                  />
                </div>
                <div className="md:col-span-2">
                  <p className="text-xs text-muted-foreground">
                    Use a faixa esperada para insumos variaveis ou uso sob demanda.
                    Se ela não for informada, o sistema usa dose x frequencia como base operacional.
                  </p>
                </div>
              </div>
            ) : null}

            <div className="flex items-end">
              <label className="flex items-center gap-3 rounded-xl border border-border/70 bg-secondary/30 px-4 py-3 text-sm">
                <input
                  checked={values.is_active}
                  className="h-5 w-5 accent-hsl(var(--primary))"
                  onChange={(event) => setValues((current) => ({ ...current, is_active: event.target.checked }))}
                  type="checkbox"
                />
                Prescrição ativa
              </label>
            </div>

            {error ? <FeedbackBanner message={error} variant="error" /> : null}

            <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
              <Button onClick={onCancel} type="button" variant="outline">
                Cancelar
              </Button>
              <Button disabled={isSubmitting} type="submit">
                {isSubmitting ? "Salvando..." : submitLabel}
              </Button>
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  )
}
