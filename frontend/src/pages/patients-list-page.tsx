import { useCallback, useEffect, useState } from "react"
import { Plus, SquarePen, UserRound } from "lucide-react"
import { Link } from "react-router-dom"

import { EmptyState } from "@/components/app/empty-state"
import { FeedbackBanner } from "@/components/app/feedback-banner"
import { PageHeader } from "@/components/app/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { listPatients } from "@/features/patients/patient-service"
import { useAuth } from "@/features/auth/use-auth"
import { HttpError } from "@/services/http"
import type { Patient } from "@/types/patient"

function getErrorMessage(error: unknown) {
  if (error instanceof HttpError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Não foi possível carregar a lista de pacientes."
}

function formatDate(value: string | null) {
  if (!value) {
    return "Não informada"
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
  }).format(new Date(`${value}T00:00:00`))
}

export function PatientsListPage() {
  const { token } = useAuth()
  const [patients, setPatients] = useState<Patient[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const loadPatients = useCallback(async () => {
    if (!token) {
      setError("Não foi possível identificar a sessão atual.")
      setPatients([])
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await listPatients(token)
      setPatients(response.data)
    } catch (requestError) {
      setPatients([])
      setError(getErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [token])

  useEffect(() => {
    void loadPatients()
  }, [loadPatients])

  return (
    <div className="grid gap-6">
      <PageHeader
        actions={
          <>
            <Button onClick={() => void loadPatients()} variant="outline">
              Atualizar
            </Button>
            <Button asChild>
              <Link to="/patients/new">
                <Plus className="h-4 w-4" />
                Novo paciente
              </Link>
            </Button>
          </>
        }
        description="Cadastre e acompanhe as pessoas atendidas pela casa assistencial."
        title="Pacientes"
      />

      {error ? <FeedbackBanner message={error} variant="error" /> : null}

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Card className="bg-white/92" key={index}>
              <CardHeader>
                <div className="h-5 w-32 animate-pulse rounded bg-secondary" />
                <div className="h-4 w-48 animate-pulse rounded bg-secondary" />
              </CardHeader>
              <CardContent>
                <div className="h-4 w-full animate-pulse rounded bg-secondary" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      {!isLoading && patients.length === 0 ? (
        <Card className="bg-white/92">
          <CardContent>
            <EmptyState
              action={
                <Button asChild>
                  <Link to="/patients/new">Criar primeiro paciente</Link>
                </Button>
              }
              description="Cadastre o primeiro paciente para iniciar o acompanhamento."
              icon={UserRound}
              title="Nenhum paciente encontrado"
            />
          </CardContent>
        </Card>
      ) : null}

      {!isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {patients.map((patient) => (
            <Card className="bg-white/92" key={patient.id}>
              <CardHeader className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle>{patient.full_name}</CardTitle>
                    <CardDescription>Nascimento: {formatDate(patient.birth_date)}</CardDescription>
                  </div>
                  <Badge variant={patient.is_active ? "success" : "outline"}>
                    {patient.is_active ? "Ativo" : "Inativo"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="min-h-12 text-sm text-muted-foreground">
                  {patient.care_notes?.trim() || "Sem observações cadastradas."}
                </p>
                <div className="flex flex-wrap gap-3">
                  <Button asChild size="sm" variant="outline">
                    <Link to={`/patients/${patient.id}`}>Ver detalhes</Link>
                  </Button>
                  <Button asChild size="sm">
                    <Link to={`/patients/${patient.id}/edit`}>
                      <SquarePen className="h-4 w-4" />
                      Editar
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  )
}
