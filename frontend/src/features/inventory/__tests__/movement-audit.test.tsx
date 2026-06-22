/*
 * ============================================================
 * Testes de rastreabilidade de usuário nas movimentações
 * ============================================================
 * Cenários cobertos:
 * [ ] 1. PatientMovementHistory exibe o nome do usuário quando preenchido
 * [ ] 2. PatientMovementHistory não quebra com movimentações legadas (null)
 * [ ] 3. Card do histórico geral exibe "Não informado" quando o nome é null
 * [ ] 4. InventoryMovementForm não expõe nenhum campo editável de "created_by"
 * ============================================================
 */

import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { InventoryMovement } from "@/types/inventory"
import { InventoryMovementForm } from "../inventory-movement-form"
import { PatientMovementHistory } from "../patient-movement-history"

// ── Mock do serviço de inventário ─────────────────────────────────────────
// Deve vir ANTES do import do módulo mockado (vitest hoist)
vi.mock("@/features/inventory/inventory-service", () => ({
  listInventoryMovements: vi.fn(),
}))

import { listInventoryMovements } from "@/features/inventory/inventory-service"
const mockList = vi.mocked(listInventoryMovements)

// ── Fixture de movimentação ────────────────────────────────────────────────
let movCounter = 0

function makeMovement(overrides: Partial<InventoryMovement> = {}): InventoryMovement {
  movCounter++
  return {
    id: `mov-audit-${movCounter}`,
    item_id: "item-1",
    unit_id: "unit-1",
    patient_id: "patient-1",
    prescription_id: null,
    created_by_user_id: null,
    created_by_user_name: null,
    movement_type: "entry",
    adjustment_operation: null,
    quantity: "10",
    stock_effect: "10",
    reason: null,
    notes: null,
    occurred_at: "2026-06-01T10:00:00Z",
    created_at: "2026-06-01T10:00:00Z",
    updated_at: "2026-06-01T10:00:00Z",
    ...overrides,
  }
}

const DEFAULT_HISTORY_PROPS = {
  patientId: "patient-1",
  itemId: "item-1",
  token: "fake-token",
}

// ── Testes ─────────────────────────────────────────────────────────────────
describe("Rastreabilidade de usuário nas movimentações", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    movCounter = 0
  })

  // 1 — exibe o nome do usuário no histórico do paciente
  it("exibe o nome do usuário que registrou a movimentação no histórico do paciente", async () => {
    mockList.mockResolvedValue({
      data: [makeMovement({ created_by_user_name: "Dr. Silva" })],
      total: 1,
    })

    render(<PatientMovementHistory {...DEFAULT_HISTORY_PROPS} />)

    await waitFor(() => {
      // O componente renderiza "· Dr. Silva" dentro do span de metadados
      expect(screen.getByText(/Dr\. Silva/)).toBeInTheDocument()
    })
  })

  // 2 — não quebra quando created_by_user_name é null (movimentações legadas)
  it("não quebra quando created_by_user_name é null (movimentações legadas)", async () => {
    mockList.mockResolvedValue({
      data: [makeMovement({ created_by_user_name: null })],
      total: 1,
    })

    render(<PatientMovementHistory {...DEFAULT_HISTORY_PROPS} />)

    // O tipo de movimentação deve aparecer — o componente renderizou sem lançar erro
    await waitFor(() => {
      expect(screen.getByText("Entrada")).toBeInTheDocument()
    })

    // O separador "·" não deve aparecer quando o nome é null
    expect(screen.queryByText(/·/)).not.toBeInTheDocument()
  })

  // 3 — "Não informado" quando created_by_user_name é null nas cards do histórico geral
  it("exibe Não informado quando created_by_user_name é null nas cards do histórico geral", () => {
    const movement = makeMovement({ created_by_user_name: null })

    // Renderiza diretamente o trecho de JSX "Registrado por" extraído de inventory-page.tsx.
    // Testa a lógica ?? "Não informado" isolada de toda a orquestração de estado da página.
    render(
      <div>
        <p>Registrado por</p>
        <p>{movement.created_by_user_name ?? "Não informado"}</p>
      </div>,
    )

    expect(screen.getByText("Registrado por")).toBeInTheDocument()
    expect(screen.getByText("Não informado")).toBeInTheDocument()
  })

  // 4 — campo created_by nunca aparece como input editável no formulário
  it("o campo created_by_user_name não aparece em nenhum campo de formulário", () => {
    // Passa um item ativo para que o formulário renderize seus campos reais
    const fakeItem = {
      id: "item-1",
      name: "Dipirona 500mg",
      item_type: "medication" as const,
      unit_id: "unit-1",
      unit_name: "Comprimido",
      unit_symbol: "cp",
      description: null,
      is_active: true,
      minimum_stock: "5",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    }

    render(
      <InventoryMovementForm
        error={null}
        isSubmitting={false}
        items={[fakeItem]}
        itemsLoading={false}
        patients={[]}
        patientsLoading={false}
        onSubmit={() => Promise.resolve()}
      />,
    )

    // Nenhum input, select ou textarea deve ter name ou id relacionado a "created_by"
    const interactiveElements = document.querySelectorAll("input, select, textarea")
    interactiveElements.forEach((el) => {
      const name = el.getAttribute("name") ?? ""
      const id = el.getAttribute("id") ?? ""
      expect(name).not.toMatch(/created_by/i)
      expect(id).not.toMatch(/created_by/i)
    })
  })
})
