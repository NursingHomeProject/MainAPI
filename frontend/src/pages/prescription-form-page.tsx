import { useCallback, useEffect, useMemo, useState } from "react"
import { ArrowLeft } from "lucide-react"
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { PageHeader } from "@/components/app/page-header"
import { Button } from "@/components/ui/button"
import { PrescriptionForm, type PrescriptionFormValues } from "@/features/prescriptions/prescription-form"
import {
  createPrescription,
  listPrescriptionsByPatient,
  updatePrescription,
} from "@/features/prescriptions/prescription-service"
import { useAuth } from "@/features/auth/use-auth"
import { listItems } from "@/features/items/item-service"
import { listPatients } from "@/features/patients/patient-service"
import { HttpError } from "@/services/http"
import type { Item } from "@/types/item"
import type { Patient } from "@/types/patient"

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível salvar a prescrição."
}

export function PrescriptionFormPage() {
  const navigate = useNavigate()
  const { prescriptionId } = useParams()
  const [searchParams] = useSearchParams()
  const { token } = useAuth()
  const isEditMode = Boolean(prescriptionId)
  const patientIdFromQuery = searchParams.get("patientId") ?? ""

  const [patients, setPatients] = useState<Patient[]>([])
  const [items, setItems] = useState<Item[]>([])
  const [defaultValues, setDefaultValues] = useState<PrescriptionFormValues | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)
  const [dependenciesError, setDependenciesError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const hasRequiredContextForEdit = useMemo(() => !isEditMode || Boolean(patientIdFromQuery), [isEditMode, patientIdFromQuery])

  const loadFormDependencies = useCallback(async () => {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      setDependenciesError("Não foi possível identificar a sessão atual.")
      setPatients([])
      setItems([])
      setIsLoading(false)
      return
    }

    if (!hasRequiredContextForEdit) {
      setError("Abra a edição a partir da lista de prescrições do paciente.")
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)
    setDependenciesError(null)

    try {
      const [patientsResponse, itemsResponse] = await Promise.all([listPatients(token), listItems(token)])
      setPatients(patientsResponse.data)
      setItems(itemsResponse.data)

      if (!isEditMode) {
        setDefaultValues((current) => ({
          ...current,
          patient_id: patientIdFromQuery || current?.patient_id || "",
          item_id: current?.item_id || "",
          dose_amount: current?.dose_amount || "1",
          comparison_window: current?.comparison_window || "scheduled_times",
          end_date: current?.end_date ?? null,
          frequency_per_day: current?.frequency_per_day || 1,
          is_active: current?.is_active ?? true,
          max_expected_per_day: current?.max_expected_per_day ?? null,
          min_expected_per_day: current?.min_expected_per_day ?? null,
          specific_times: current?.specific_times ?? null,
          start_date: current?.start_date || "",
          usage_mode: current?.usage_mode || "fixed",
        }))
        return
      }

      const prescriptionsResponse = await listPrescriptionsByPatient(token, patientIdFromQuery)
      const prescription = prescriptionsResponse.data.find((item) => item.id === prescriptionId)

      if (!prescription) {
        setError("Não foi possível localizar a prescrição selecionada para edição.")
        return
      }

      setDefaultValues({
        dose_amount: prescription.dose_amount,
        comparison_window: prescription.comparison_window,
        end_date: prescription.end_date,
        frequency_per_day: prescription.frequency_per_day,
        is_active: prescription.is_active,
        item_id: prescription.item_id,
        max_expected_per_day: prescription.max_expected_per_day,
        min_expected_per_day: prescription.min_expected_per_day,
        patient_id: prescription.patient_id,
        specific_times: prescription.specific_times,
        start_date: prescription.start_date,
        usage_mode: prescription.usage_mode,
      })
    } catch (requestError) {
      const message = getErrorMessage(requestError)
      setPatients([])
      setItems([])
      setError(message)
      setDependenciesError(message)
    } finally {
      setIsLoading(false)
    }
  }, [hasRequiredContextForEdit, isEditMode, patientIdFromQuery, prescriptionId, token])

  useEffect(() => {
    void loadFormDependencies()
  }, [loadFormDependencies])

  async function handleSubmit(values: PrescriptionFormValues) {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      if (isEditMode && prescriptionId) {
        const response = await updatePrescription(token, prescriptionId, values)
        navigate(`/prescriptions?patientId=${response.data.patient_id}`, {
          replace: true,
          state: { message: "Prescrição atualizada com sucesso.", tone: "success" },
        })
        return
      }

      const response = await createPrescription(token, values)
      navigate(`/prescriptions?patientId=${response.data.patient_id}`, {
        replace: true,
        state: { message: "Prescrição criada com sucesso.", tone: "success" },
      })
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="grid gap-6">
      <PageHeader
        actions={
          <Button asChild variant="outline">
            <Link to={patientIdFromQuery ? `/prescriptions?patientId=${patientIdFromQuery}` : "/prescriptions"}>
              <ArrowLeft className="h-4 w-4" />
              Voltar para prescrições
            </Link>
          </Button>
        }
        description={
          isEditMode
            ? "Atualize os dados da prescrição selecionada."
            : "Cadastre uma nova prescrição para o paciente."
        }
        title={isEditMode ? "Editar prescrição" : "Nova prescrição"}
      />

      {!hasRequiredContextForEdit ? (
        <FeedbackBanner
          message={
            <>
              Abra a edição a partir da lista de prescrições do paciente para carregar os dados corretamente.
            </>
          }
          variant="warning"
        />
      ) : null}

      {isLoading ? (
        <div className="rounded-2xl border border-border/80 bg-white/92 px-6 py-10 text-sm text-muted-foreground">
          Carregando dados da prescrição...
        </div>
      ) : isEditMode && !defaultValues ? (
        <FeedbackBanner
          message={error || "Não foi possível carregar os dados da prescrição para edição."}
          variant="error"
        />
      ) : (
        <PrescriptionForm
          defaultValues={defaultValues}
          description="Preencha os dados de dose, tipo de uso, janela de comparação e período da prescrição."
          error={error}
          isSubmitting={isSubmitting}
          items={items}
          itemsError={dependenciesError}
          itemsLoading={isLoading}
          onCancel={() => navigate(patientIdFromQuery ? `/prescriptions?patientId=${patientIdFromQuery}` : "/prescriptions")}
          onSubmit={handleSubmit}
          patients={patients}
          patientsError={dependenciesError}
          patientsLoading={isLoading}
          submitLabel={isEditMode ? "Salvar alteracoes" : "Criar prescrição"}
          title={isEditMode ? "Formulario de edição" : "Formulario de criacao"}
        />
      )}
    </div>
  )
}
