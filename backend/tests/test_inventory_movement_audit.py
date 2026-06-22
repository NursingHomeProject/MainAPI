"""
Testes de rastreabilidade de usuário nas movimentações de estoque.

Cenários cobertos:
  1. POST /inventory/movements → created_by_user_id igual ao id do usuário autenticado
  2. POST /inventory/movements → created_by_user_name igual ao full_name do usuário autenticado
  3. GET  /inventory/movements → cada item da lista tem created_by_user_name preenchido
  4. POST /patients/{id}/stock/movements → created_by_user_name no response
  5. GET  /patients/{id}/details → recent_movements[0].created_by_user_name correto
  6. GET  /inventory/movements → created_by_user_name é null para movimentações legadas
"""
from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.modules.auth.dependencies import get_current_active_user
from app.modules.dashboard.schemas import (
    PatientDetailsMetrics,
    PatientDetailsMovementItem,
    PatientDetailsResponse,
)
from app.modules.inventory.models import InventoryMovementType


# ---------------------------------------------------------------------------
# Fixture compartilhada
# ---------------------------------------------------------------------------

def _make_fake_movement(
    *,
    created_by_user_id=None,
    created_by=None,
    patient_id=None,
    item_id=None,
    unit_id=None,
) -> SimpleNamespace:
    """
    Cria um SimpleNamespace que satisfaz todos os atributos lidos por
    build_inventory_movement_response e por get_inventory_stock_effect.
    """
    return SimpleNamespace(
        id=uuid4(),
        item_id=item_id or uuid4(),
        unit_id=unit_id or uuid4(),
        patient_id=patient_id,
        prescription_id=None,
        created_by_user_id=created_by_user_id,
        created_by=created_by,
        movement_type=InventoryMovementType.ENTRY,
        adjustment_operation=None,
        quantity=Decimal("10"),
        reason=None,
        notes=None,
        occurred_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

class InventoryMovementAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sentinel_db = object()
        self.user_id = uuid4()
        self.item_id = uuid4()
        self.patient_id = uuid4()

        # full_name é o campo auditado: deve aparecer em created_by_user_name
        self.fake_user = SimpleNamespace(
            id=self.user_id,
            is_active=True,
            full_name="Dr. Ana Silva",
        )

        app.dependency_overrides[get_db] = self._override_get_db
        app.dependency_overrides[get_current_active_user] = lambda: self.fake_user

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _override_get_db(self):
        yield self.sentinel_db

    # ------------------------------------------------------------------
    # Cenário 1 — POST /inventory/movements → created_by_user_id correto
    # ------------------------------------------------------------------

    def test_create_movement_stores_created_by_user_id(self):
        """
        O created_by_user_id na resposta deve ser igual ao id do usuário autenticado.
        A rota passa current_user.id para create_inventory_movement, que persiste
        o valor no campo FK. O builder copia esse valor para o schema de resposta.
        """
        movement = _make_fake_movement(
            created_by_user_id=self.user_id,
            item_id=self.item_id,
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.inventory.routes.create_inventory_movement",
                return_value=movement,
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/inventory/movements",
                    json={
                        "item_id": str(self.item_id),
                        "movement_type": "entry",
                        "quantity": "10",
                    },
                )

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["created_by_user_id"], str(self.user_id))

    # ------------------------------------------------------------------
    # Cenário 2 — POST /inventory/movements → created_by_user_name correto
    # ------------------------------------------------------------------

    def test_create_movement_returns_created_by_user_name(self):
        """
        O created_by_user_name na resposta deve ser o full_name do usuário autenticado,
        nunca null nem string vazia. A rota passa current_user.full_name diretamente
        para o builder — sem query extra ao banco.
        """
        movement = _make_fake_movement(
            created_by_user_id=self.user_id,
            item_id=self.item_id,
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.inventory.routes.create_inventory_movement",
                return_value=movement,
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/inventory/movements",
                    json={
                        "item_id": str(self.item_id),
                        "movement_type": "entry",
                        "quantity": "10",
                    },
                )

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["created_by_user_name"], self.fake_user.full_name)
        self.assertIsNotNone(data["created_by_user_name"])
        self.assertNotEqual(data["created_by_user_name"], "")

    # ------------------------------------------------------------------
    # Cenário 3 — GET /inventory/movements → lista com created_by_user_name
    # ------------------------------------------------------------------

    def test_list_movements_returns_created_by_user_name(self):
        """
        Ao listar 2 movimentações do mesmo usuário, cada item deve ter
        created_by_user_name preenchido a partir do relacionamento ORM created_by,
        que é carregado via selectinload no serviço.
        """
        user_ns = SimpleNamespace(full_name=self.fake_user.full_name)
        movements = [
            _make_fake_movement(
                created_by_user_id=self.user_id,
                created_by=user_ns,
                item_id=self.item_id,
            ),
            _make_fake_movement(
                created_by_user_id=self.user_id,
                created_by=user_ns,
                item_id=self.item_id,
            ),
        ]

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.inventory.routes.list_inventory_movements",
                return_value=movements,
            ),
        ):
            with TestClient(app) as client:
                response = client.get("/inventory/movements")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        for item in payload["data"]:
            self.assertEqual(item["created_by_user_name"], self.fake_user.full_name)

    # ------------------------------------------------------------------
    # Cenário 4 — POST /patients/{id}/stock/movements → created_by_user_name
    # ------------------------------------------------------------------

    def test_patient_stock_entry_stores_created_by(self):
        """
        A entrada de estoque de família deve expor o nome do usuário autenticado
        em created_by_user_name. A rota passa current_user.full_name para o builder
        diretamente, sem query extra ao banco.
        """
        patient = SimpleNamespace(id=self.patient_id, full_name="Paciente Teste")
        movement = _make_fake_movement(
            created_by_user_id=self.user_id,
            patient_id=self.patient_id,
            item_id=self.item_id,
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.inventory.routes.get_patient_for_inventory_or_raise",
                return_value=patient,
            ),
            patch(
                "app.modules.inventory.routes.create_inventory_movement",
                return_value=movement,
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    f"/patients/{self.patient_id}/stock/movements",
                    json={"item_id": str(self.item_id), "quantity": "10"},
                )

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["created_by_user_name"], self.fake_user.full_name)

    # ------------------------------------------------------------------
    # Cenário 5 — GET /patients/{id}/details → recent_movements com user name
    # ------------------------------------------------------------------

    def test_patient_details_movements_include_user_name(self):
        """
        Os recent_movements no detalhe do paciente devem expor created_by_user_name
        igual ao full_name do usuário que registrou a movimentação. O serviço de
        dashboard usa LEFT JOIN com users para preencher esse campo.
        """
        patient_details = PatientDetailsResponse(
            id=self.patient_id,
            full_name="Paciente Teste",
            birth_date=date(1990, 1, 1),
            care_notes=None,
            is_active=True,
            metrics=PatientDetailsMetrics(
                active_prescriptions=0,
                active_items=0,
                open_alerts=0,
            ),
            open_alerts=[],
            recent_movements=[
                PatientDetailsMovementItem(
                    id=uuid4(),
                    item_id=self.item_id,
                    item_name="Dipirona 500mg",
                    unit_symbol="comprimido",
                    movement_type=InventoryMovementType.ENTRY,
                    quantity=Decimal("10"),
                    occurred_at=datetime.now(timezone.utc),
                    created_by_user_id=self.user_id,
                    created_by_user_name=self.fake_user.full_name,
                )
            ],
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.dashboard.routes.get_patient_details",
                return_value=patient_details,
            ),
        ):
            with TestClient(app) as client:
                response = client.get(f"/patients/{self.patient_id}/details")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["recent_movements"]), 1)
        movement = data["recent_movements"][0]
        self.assertEqual(movement["created_by_user_name"], self.fake_user.full_name)
        self.assertEqual(movement["created_by_user_id"], str(self.user_id))

    # ------------------------------------------------------------------
    # Cenário 6 — GET /inventory/movements → null para movimentações legadas
    # ------------------------------------------------------------------

    def test_created_by_user_name_is_null_for_legacy_movements(self):
        """
        Movimentações inseridas antes da rastreabilidade (created_by_user_id=None,
        created_by=None) devem retornar created_by_user_name=null sem causar erro 500.
        O builder resolve o nome via relacionamento ORM; quando ambos são None,
        retorna None sem lançar exceção.
        """
        legacy_movement = _make_fake_movement(
            created_by_user_id=None,
            created_by=None,
            item_id=self.item_id,
        )

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.inventory.routes.list_inventory_movements",
                return_value=[legacy_movement],
            ),
        ):
            with TestClient(app) as client:
                response = client.get("/inventory/movements")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        movement_data = payload["data"][0]
        self.assertIsNone(movement_data["created_by_user_name"])
        self.assertIsNone(movement_data["created_by_user_id"])


if __name__ == "__main__":
    unittest.main()
