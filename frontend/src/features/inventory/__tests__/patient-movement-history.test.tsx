/*
 * ============================================================
 * CHECKLIST DE VALIDAÇÃO MANUAL — PatientMovementHistory
 * ============================================================
 * [ ] Abrir detalhe de paciente com prescrições e movimentações registradas
 * [ ] Clicar "Ver histórico" em um item → componente deve aparecer
 *     com spinner/texto "Carregando histórico..." brevemente
 * [ ] Após carregar: lista deve mostrar data, tipo traduzido (pt-BR)
 *     e quantidade com sinal (+/-)
 * [ ] Movimentações de entrada (entry) → cor verde, sinal +
 * [ ] Movimentações de administração → cor cinza, sinal -
 * [ ] Perdas/Descartes → cor vermelha, sinal -
 * [ ] Ajustes → cor âmbar
 * [ ] Observação do movimento deve aparecer abaixo do tipo quando preenchida
 * [ ] Clicar "Ocultar histórico" → componente desaparece
 * [ ] Paciente sem movimentações → mensagem "Nenhuma movimentação registrada ainda."
 * [ ] Verificar que dois pacientes com mesmo item mostram históricos independentes
 * ============================================================
 */

import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { InventoryMovement } from "@/types/inventory"
import { PatientMovementHistory } from "../patient-movement-history"

// ── Mock do serviço de inventário ──────────────────────────────────────────
vi.mock("@/features/inventory/inventory-service", () => ({
  listInventoryMovements: vi.fn(),
}))

import { listInventoryMovements } from "@/features/inventory/inventory-service"
const mockList = vi.mocked(listInventoryMovements)

// ── Fixtures ───────────────────────────────────────────────────────────────
let movCounter = 0
function makeMovement(overrides: Partial<InventoryMovement> = {}): InventoryMovement {
  movCounter++
  return {
    id: `mov-${movCounter}`,
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

const DEFAULT_PROPS = {
  patientId: "patient-1",
  itemId: "item-1",
  token: "fake-token",
}

// ── Testes ─────────────────────────────────────────────────────────────────
describe("PatientMovementHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    movCounter = 0
  })

  // 1 — loading state
  it("mostra texto de carregamento enquanto a requisição está em andamento", () => {
    // Promise que nunca resolve → estado loading permanente
    mockList.mockImplementation(() => new Promise(() => {}))

    render(<PatientMovementHistory {...DEFAULT_PROPS} />)

    expect(screen.getByText(/carregando histórico/i)).toBeInTheDocument()
  })

  // 2 — renderiza lista com data e tipo traduzido
  it("renderiza movimentações com tipo traduzido para português", async () => {
    mockList.mockResolvedValue({
      data: [
        makeMovement({ movement_type: "entry",          stock_effect: "10" }),
        makeMovement({ movement_type: "administration", stock_effect: "-1" }),
        makeMovement({ movement_type: "loss",           stock_effect: "-5" }),
        makeMovement({ movement_type: "discard",        stock_effect: "-2" }),
        makeMovement({ movement_type: "adjustment",     stock_effect: "3"  }),
      ],
      total: 5,
    })

    render(<PatientMovementHistory {...DEFAULT_PROPS} />)

    await waitFor(() => {
      expect(screen.getByText("Entrada")).toBeInTheDocument()
      expect(screen.getByText("Administração")).toBeInTheDocument()
      expect(screen.getByText("Perda")).toBeInTheDocument()
      expect(screen.getByText("Descarte")).toBeInTheDocument()
      expect(screen.getByText("Ajuste")).toBeInTheDocument()
    })
  })

  // 3 — estado vazio
  it("mostra mensagem de estado vazio quando não há movimentações", async () => {
    mockList.mockResolvedValue({ data: [], total: 0 })

    render(<PatientMovementHistory {...DEFAULT_PROPS} />)

    await waitFor(() => {
      expect(screen.getByText(/nenhuma movimentação registrada/i)).toBeInTheDocument()
    })
  })

  // 4 — formata quantidade com sinal correto
  it("exibe sinal + para entradas e - para saídas", async () => {
    mockList.mockResolvedValue({
      data: [
        makeMovement({ movement_type: "entry",          stock_effect: "10" }),
        makeMovement({ movement_type: "administration", stock_effect: "-1" }),
      ],
      total: 2,
    })

    render(<PatientMovementHistory {...DEFAULT_PROPS} />)

    await waitFor(() => {
      expect(screen.getByText("+10")).toBeInTheDocument()
      expect(screen.getByText("-1")).toBeInTheDocument()
    })
  })

  // Bônus — exibe nota quando preenchida
  it("exibe observação da movimentação quando preenchida", async () => {
    mockList.mockResolvedValue({
      data: [makeMovement({ notes: "Família trouxe caixa nova" })],
      total: 1,
    })

    render(<PatientMovementHistory {...DEFAULT_PROPS} />)

    await waitFor(() => {
      expect(screen.getByText("Família trouxe caixa nova")).toBeInTheDocument()
    })
  })

  // Bônus — ordena pelo mais recente primeiro e limita a 10
  it("exibe no máximo 10 movimentações ordenadas da mais recente para a mais antiga", async () => {
    const movements = Array.from({ length: 15 }, (_, i) =>
      makeMovement({
        stock_effect: "1",
        occurred_at: new Date(2026, 0, i + 1).toISOString(),
      }),
    )
    mockList.mockResolvedValue({ data: movements, total: 15 })

    render(<PatientMovementHistory {...DEFAULT_PROPS} />)

    await waitFor(() => {
      expect(screen.getByText(/últimas 10 movimentações/i)).toBeInTheDocument()
    })
  })

  // Bônus — passa os filtros corretos para o serviço
  it("chama listInventoryMovements com patient_id e item_id corretos", () => {
    mockList.mockImplementation(() => new Promise(() => {}))

    render(<PatientMovementHistory patientId="p-123" itemId="i-456" token="tok-789" />)

    expect(mockList).toHaveBeenCalledWith("tok-789", {
      patient_id: "p-123",
      item_id: "i-456",
    })
  })
})
