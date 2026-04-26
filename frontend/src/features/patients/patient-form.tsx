import { type FormEvent, useState } from "react"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { PatientCreatePayload } from "@/types/patient"

export type PatientFormValues = PatientCreatePayload

type PatientFormProps = {
  defaultValues?: PatientFormValues
  description: string
  error: string | null
  isSubmitting: boolean
  submitLabel: string
  title: string
  onCancel: () => void
  onSubmit: (values: PatientFormValues) => Promise<void>
}

const defaultPatientFormValues: PatientFormValues = {
  full_name: "",
  birth_date: null,
  care_notes: "",
  is_active: true,
}

export function PatientForm({
  defaultValues,
  description,
  error,
  isSubmitting,
  onCancel,
  onSubmit,
  submitLabel,
  title,
}: PatientFormProps) {
  const [values, setValues] = useState<PatientFormValues>(defaultValues ?? defaultPatientFormValues)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    await onSubmit({
      birth_date: values.birth_date || null,
      care_notes: values.care_notes?.trim() ? values.care_notes.trim() : null,
      full_name: values.full_name,
      is_active: values.is_active,
    })
  }

  return (
    <Card className="bg-white/92">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="grid gap-5 md:grid-cols-2">
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="full_name">Nome completo</Label>
              <Input
                id="full_name"
                maxLength={255}
                minLength={3}
                onChange={(event) => setValues((current) => ({ ...current, full_name: event.target.value }))}
                placeholder="Nome do paciente"
                required
                value={values.full_name}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="birth_date">Data de nascimento</Label>
              <Input
                id="birth_date"
                onChange={(event) => setValues((current) => ({ ...current, birth_date: event.target.value || null }))}
                type="date"
                value={values.birth_date ?? ""}
              />
            </div>

            <div className="flex items-end">
              <label className="flex items-center gap-3 rounded-xl border border-border/70 bg-secondary/30 px-4 py-3 text-sm">
                <input
                  checked={values.is_active}
                  className="h-4 w-4 accent-hsl(var(--primary))"
                  onChange={(event) => setValues((current) => ({ ...current, is_active: event.target.checked }))}
                  type="checkbox"
                />
                Paciente ativo
              </label>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="care_notes">Observações</Label>
            <Textarea
              id="care_notes"
              maxLength={2000}
              onChange={(event) => setValues((current) => ({ ...current, care_notes: event.target.value }))}
              placeholder="Informações de acompanhamento, cuidados ou observações gerais."
              value={values.care_notes ?? ""}
            />
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
      </CardContent>
    </Card>
  )
}
