import { useCallback, useEffect, useState } from "react"
import { ArrowLeft } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"

import { FeedbackBanner } from "@/components/app/feedback-banner"
import { PageHeader } from "@/components/app/page-header"
import { Button } from "@/components/ui/button"
import { PatientForm, type PatientFormValues } from "@/features/patients/patient-form"
import { createPatient, getPatient, updatePatient } from "@/features/patients/patient-service"
import { useAuth } from "@/features/auth/use-auth"
import { HttpError } from "@/services/http"

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível salvar o paciente."
}

export function PatientFormPage() {
  const navigate = useNavigate()
  const { patientId } = useParams()
  const { token } = useAuth()
  const isEditMode = Boolean(patientId)

  const [defaultValues, setDefaultValues] = useState<PatientFormValues | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(isEditMode)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const loadPatient = useCallback(async () => {
    if (!isEditMode || !patientId) {
      return
    }

    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await getPatient(token, patientId)
      setDefaultValues({
        birth_date: response.data.birth_date,
        care_notes: response.data.care_notes ?? "",
        full_name: response.data.full_name,
        is_active: response.data.is_active,
      })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [isEditMode, patientId, token])

  useEffect(() => {
    void loadPatient()
  }, [loadPatient])

  async function handleSubmit(values: PatientFormValues) {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      if (isEditMode && patientId) {
        const response = await updatePatient(token, patientId, values)
        navigate(`/patients/${response.data.id}`, {
          replace: true,
          state: { message: "Paciente atualizado com sucesso.", tone: "success" },
        })
        return
      }

      const response = await createPatient(token, values)
      navigate(`/patients/${response.data.id}`, {
        replace: true,
        state: { message: "Paciente criado com sucesso.", tone: "success" },
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
            <Link to="/patients">
              <ArrowLeft className="h-4 w-4" />
              Voltar para a lista
            </Link>
          </Button>
        }
        description={
          isEditMode
            ? "Atualize os dados do paciente selecionado."
            : "Cadastre um novo paciente para acompanhamento."
        }
        title={isEditMode ? "Editar paciente" : "Novo paciente"}
      />

      {isLoading ? (
        <div className="rounded-2xl border border-border/80 bg-white/92 px-6 py-10 text-sm text-muted-foreground">
          Carregando dados do paciente...
        </div>
      ) : isEditMode && !defaultValues ? (
        <FeedbackBanner
          message={error || "Não foi possível carregar os dados do paciente para edição."}
          variant="error"
        />
      ) : (
        <PatientForm
          defaultValues={defaultValues}
          description={
            isEditMode
              ? "Revise as informações e salve as alteracoes necessarias."
              : "Preencha os dados principais para iniciar o cadastro."
          }
          error={error}
          isSubmitting={isSubmitting}
          onCancel={() => navigate("/patients")}
          onSubmit={handleSubmit}
          submitLabel={isEditMode ? "Salvar alterações" : "Criar paciente"}
          title={isEditMode ? "Formulário de edição" : "Formulário de criação"}
        />
      )}
    </div>
  )
}
