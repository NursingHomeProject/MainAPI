"""
Testes para a funcionalidade de estoque individual por paciente.

Cenários cobertos:
  1. GET /patients/{id}/stock → 404 quando paciente não existe
  2. GET /patients/{id}/stock → lista vazia quando não há prescrições ativas
  3. GET /patients/{id}/stock → retorna itens com saldo correto
  4. Dois pacientes com o mesmo item têm saldos independentes
  5. POST /patients/{id}/stock/movements → força movement_type=ENTRY e vincula patient_id da URL
  6. POST /patients/{id}/stock/movements → 404 quando paciente não existe
  7. calculate_current_stock_for_patient_item filtra por patient_id no banco
"""
from __future__ import annotations

import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.modules.auth.dependencies import get_current_active_user
from app.modules.inventory.models import InventoryMovementType
from app.modules.inventory.services import (
    calculate_current_stock_for_patient_item,
    list_patient_stock,
)


# ---------------------------------------------------------------------------
# Fixtures compartilhadas
# ---------------------------------------------------------------------------

def _make_patient(patient_id: UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=patient_id or uuid4(), full_name="Paciente Teste")


def _make_item(item_id: UUID | None = None, name: str = "Dipirona 500mg") -> SimpleNamespace:
    return SimpleNamespace(
        id=item_id or uuid4(),
        name=name,
        minimum_stock=Decimal("5"),
        unit=SimpleNamespace(symbol="comprimido"),
    )


def _make_prescription(patient_id: UUID, item_id: UUID, dose: str = "1", freq: int = 3) -> SimpleNamespace:
    from datetime import date
    return SimpleNamespace(
        id=uuid4(),
        patient_id=patient_id,
        item_id=item_id,
        dose_amount=Decimal(dose),
        frequency_per_day=freq,
        is_active=True,
        start_date=date(2026, 1, 1),
        end_date=None,
    )


def _make_movement_response(patient_id: UUID, item_id: UUID) -> SimpleNamespace:
    from datetime import datetime, timezone
    return SimpleNamespace(
        id=uuid4(),
        item_id=item_id,
        unit_id=uuid4(),
        patient_id=patient_id,
        prescription_id=None,
        created_by_user_id=uuid4(),
        movement_type=InventoryMovementType.ENTRY,
        adjustment_operation=None,
        quantity=Decimal("10"),
        stock_effect=Decimal("10"),
        reason=None,
        notes=None,
        occurred_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Classe de testes das rotas HTTP
# ---------------------------------------------------------------------------

class PatientStockRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sentinel_db = object()
        self.fake_user = SimpleNamespace(id=uuid4(), is_active=True)
        self.patient_id = uuid4()
        self.item_id = uuid4()

        app.dependency_overrides[get_db] = self._override_get_db
        app.dependency_overrides[get_current_active_user] = lambda: self.fake_user

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _override_get_db(self):
        yield self.sentinel_db

    # ------------------------------------------------------------------
    # Cenário 1 — GET /patients/{id}/stock → 404 quando paciente não existe
    # ------------------------------------------------------------------

    def test_get_patient_stock_returns_404_when_patient_not_found(self):
        """
        Se o paciente não existir, a rota deve retornar 404.
        Isso é garantido pela chamada a get_patient_for_inventory_or_raise.
        """
        def _raise_not_found(db, patient_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente nao encontrado.")

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.inventory.routes.get_patient_for_inventory_or_raise",
                side_effect=_raise_not_found,
            ),
        ):
            with TestClient(app) as client:
                response = client.get(f"/patients/{self.patient_id}/stock")

        self.assertEqual(response.status_code, 404)
        self.assertIn("nao encontrado", response.json()["detail"].lower())

    # ------------------------------------------------------------------
    # Cenário 2 — GET → 200 com lista vazia quando sem prescrições ativas
    # ------------------------------------------------------------------

    def test_get_patient_stock_returns_empty_list_when_no_active_prescriptions(self):
        """
        Paciente sem prescrições ativas deve retornar data=[] e total=0.
        """
        patient = _make_patient(self.patient_id)

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.inventory.routes.get_patient_for_inventory_or_raise",
                return_value=patient,
            ),
            patch(
                "app.modules.inventory.routes.list_patient_stock",
                return_value=[],
            ),
        ):
            with TestClient(app) as client:
                response = client.get(f"/patients/{self.patient_id}/stock")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["patient_id"], str(self.patient_id))
        self.assertEqual(payload["data"], [])
        self.assertEqual(payload["total"], 0)

    # ------------------------------------------------------------------
    # Cenário 3 — GET → 200 com itens e saldo correto
    # ------------------------------------------------------------------

    def test_get_patient_stock_returns_items_with_correct_balance(self):
        """
        Quando há prescrições ativas, o endpoint deve retornar os itens
        com current_stock, is_below_minimum e estimated_days_remaining corretos.
        """
        patient = _make_patient(self.patient_id)
        fake_stock_data = [
            {
                "item_id": self.item_id,
                "item_name": "Dipirona 500mg",
                "unit_symbol": "comprimido",
                "current_stock": Decimal("18"),
                "minimum_stock": Decimal("5"),
                "is_below_minimum": False,
                "total_daily_dose": Decimal("3"),
                "estimated_days_remaining": Decimal("6"),
                "prescription_ids": [uuid4()],
            }
        ]

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.inventory.routes.get_patient_for_inventory_or_raise",
                return_value=patient,
            ),
            patch(
                "app.modules.inventory.routes.list_patient_stock",
                return_value=fake_stock_data,
            ),
        ):
            with TestClient(app) as client:
                response = client.get(f"/patients/{self.patient_id}/stock")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)

        item_data = payload["data"][0]
        self.assertEqual(item_data["item_name"], "Dipirona 500mg")
        self.assertEqual(Decimal(item_data["current_stock"]), Decimal("18"))
        self.assertFalse(item_data["is_below_minimum"])
        self.assertEqual(Decimal(item_data["estimated_days_remaining"]), Decimal("6"))

    # ------------------------------------------------------------------
    # Cenário 4 — Dois pacientes com mesmo item têm saldos independentes
    # ------------------------------------------------------------------

    def test_stock_is_independent_per_patient(self):
        """
        Fernando e Francisco usam Dipirona 500mg, mas o saldo de cada um
        deve ser calculado de forma independente.

        Testamos via route: as duas chamadas devem retornar total
        diferente porque list_patient_stock é chamado com patient_id correto.
        """
        patient_fernando_id = uuid4()
        patient_francisco_id = uuid4()
        item_id = self.item_id

        stock_per_patient = {
            patient_fernando_id: [
                {
                    "item_id": item_id,
                    "item_name": "Dipirona 500mg",
                    "unit_symbol": "comprimido",
                    "current_stock": Decimal("30"),
                    "minimum_stock": Decimal("5"),
                    "is_below_minimum": False,
                    "total_daily_dose": Decimal("3"),
                    "estimated_days_remaining": Decimal("10"),
                    "prescription_ids": [uuid4()],
                }
            ],
            patient_francisco_id: [
                {
                    "item_id": item_id,
                    "item_name": "Dipirona 500mg",
                    "unit_symbol": "comprimido",
                    "current_stock": Decimal("3"),
                    "minimum_stock": Decimal("5"),
                    "is_below_minimum": True,
                    "total_daily_dose": Decimal("3"),
                    "estimated_days_remaining": Decimal("1"),
                    "prescription_ids": [uuid4()],
                }
            ],
        }

        def _fake_list_patient_stock(db, pid):
            return stock_per_patient.get(pid, [])

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.inventory.routes.get_patient_for_inventory_or_raise",
                return_value=_make_patient(),
            ),
            patch(
                "app.modules.inventory.routes.list_patient_stock",
                side_effect=_fake_list_patient_stock,
            ),
        ):
            with TestClient(app) as client:
                resp_fernando = client.get(f"/patients/{patient_fernando_id}/stock")
                resp_francisco = client.get(f"/patients/{patient_francisco_id}/stock")

        self.assertEqual(resp_fernando.status_code, 200)
        self.assertEqual(resp_francisco.status_code, 200)

        fernando_stock = Decimal(resp_fernando.json()["data"][0]["current_stock"])
        francisco_stock = Decimal(resp_francisco.json()["data"][0]["current_stock"])

        # Saldos devem ser diferentes
        self.assertNotEqual(fernando_stock, francisco_stock)
        self.assertEqual(fernando_stock, Decimal("30"))
        self.assertEqual(francisco_stock, Decimal("3"))

        # Francisco está abaixo do mínimo, Fernando não
        self.assertFalse(resp_fernando.json()["data"][0]["is_below_minimum"])
        self.assertTrue(resp_francisco.json()["data"][0]["is_below_minimum"])

    # ------------------------------------------------------------------
    # Cenário 5 — POST força movement_type=ENTRY e vincula patient_id da URL
    # ------------------------------------------------------------------

    def test_create_patient_stock_entry_forces_entry_type_and_patient_id(self):
        """
        O endpoint POST deve:
        - Sempre criar com movement_type=ENTRY (não aceita outro tipo)
        - Vincular patient_id da URL (não do corpo da requisição)
        """
        patient = _make_patient(self.patient_id)
        movement_response = _make_movement_response(self.patient_id, self.item_id)

        captured_payload = {}

        def _fake_create_inventory_movement(db, payload, *, created_by_user_id):
            captured_payload["movement_type"] = payload.movement_type
            captured_payload["patient_id"] = payload.patient_id
            captured_payload["item_id"] = payload.item_id
            captured_payload["quantity"] = payload.quantity
            return movement_response

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.inventory.routes.get_patient_for_inventory_or_raise",
                return_value=patient,
            ),
            patch(
                "app.modules.inventory.routes.create_inventory_movement",
                side_effect=_fake_create_inventory_movement,
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    f"/patients/{self.patient_id}/stock/movements",
                    json={"item_id": str(self.item_id), "quantity": "10"},
                )

        self.assertEqual(response.status_code, 201)

        # Verifica que o tipo foi forçado para ENTRY
        self.assertEqual(captured_payload["movement_type"], InventoryMovementType.ENTRY)

        # Verifica que o patient_id veio da URL, não do payload do cliente
        self.assertEqual(captured_payload["patient_id"], self.patient_id)
        self.assertEqual(captured_payload["item_id"], self.item_id)
        self.assertEqual(captured_payload["quantity"], Decimal("10"))

    # ------------------------------------------------------------------
    # Cenário 6 — POST → 404 quando paciente não existe
    # ------------------------------------------------------------------

    def test_create_patient_stock_entry_returns_404_when_patient_not_found(self):
        """
        Se o paciente não existir, o POST de entrada de estoque deve retornar 404.
        """
        def _raise_not_found(db, patient_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente nao encontrado.")

        with (
            patch("app.main.seed_admin_user"),
            patch("app.main.seed_default_units"),
            patch(
                "app.modules.inventory.routes.get_patient_for_inventory_or_raise",
                side_effect=_raise_not_found,
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    f"/patients/{self.patient_id}/stock/movements",
                    json={"item_id": str(self.item_id), "quantity": "5"},
                )

        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Cenário 7 — Teste unitário de calculate_current_stock_for_patient_item
# ---------------------------------------------------------------------------

class PatientStockCalculationTests(unittest.TestCase):
    """
    Verifica que calculate_current_stock_for_patient_item filtra corretamente
    por patient_id, retornando saldos distintos para pacientes distintos.
    """

    def setUp(self) -> None:
        self.patient_fernando_id = uuid4()
        self.patient_francisco_id = uuid4()
        self.item_id = uuid4()

    def _make_db_returning(self, value) -> MagicMock:
        """Cria um fake de Session cujo scalar() retorna o valor informado."""
        db = MagicMock()
        db.scalar.return_value = value
        return db

    def test_returns_decimal_when_db_returns_decimal(self):
        """Deve retornar Decimal quando o banco já retorna Decimal."""
        db = self._make_db_returning(Decimal("18"))
        result = calculate_current_stock_for_patient_item(db, self.patient_fernando_id, self.item_id)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal("18"))

    def test_returns_decimal_when_db_returns_int(self):
        """Deve converter int para Decimal sem perda de precisão."""
        db = self._make_db_returning(0)
        result = calculate_current_stock_for_patient_item(db, self.patient_fernando_id, self.item_id)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal("0"))

    def test_two_patients_receive_distinct_stocks_from_distinct_db_calls(self):
        """
        Quando o banco retorna valores diferentes para patient A e patient B,
        a função deve propagar esses valores distintos.
        Isso simula o isolamento real de estoque entre pacientes.
        """
        db_fernando = self._make_db_returning(Decimal("30"))
        db_francisco = self._make_db_returning(Decimal("3"))

        stock_fernando = calculate_current_stock_for_patient_item(
            db_fernando, self.patient_fernando_id, self.item_id
        )
        stock_francisco = calculate_current_stock_for_patient_item(
            db_francisco, self.patient_francisco_id, self.item_id
        )

        self.assertEqual(stock_fernando, Decimal("30"))
        self.assertEqual(stock_francisco, Decimal("3"))
        self.assertNotEqual(stock_fernando, stock_francisco)

    def test_db_scalar_is_called_exactly_once_per_invocation(self):
        """
        A função deve chamar db.scalar() exatamente uma vez por chamada —
        sem caching acidental ou chamadas extras.
        """
        db = self._make_db_returning(Decimal("10"))
        calculate_current_stock_for_patient_item(db, self.patient_fernando_id, self.item_id)
        self.assertEqual(db.scalar.call_count, 1)

    def test_query_is_built_with_patient_id_filter(self):
        """
        Garante que a query enviada ao banco contém o filtro de patient_id.
        Inspeciona o SQL compilado para confirmar presença do UUID do paciente.
        """
        from sqlalchemy.dialects import sqlite

        db = MagicMock()
        captured_statements = []

        def _capture_scalar(stmt):
            compiled = stmt.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
            captured_statements.append(str(compiled))
            return Decimal("0")

        db.scalar.side_effect = _capture_scalar

        calculate_current_stock_for_patient_item(db, self.patient_fernando_id, self.item_id)

        self.assertEqual(len(captured_statements), 1)
        sql = captured_statements[0]

        # O UUID do paciente deve aparecer no SQL compilado.
        # SQLite compila UUIDs sem traços, então comparamos sem eles também.
        patient_uuid_hex = str(self.patient_fernando_id).replace("-", "")
        item_uuid_hex = str(self.item_id).replace("-", "")
        self.assertIn(patient_uuid_hex, sql)
        self.assertIn(item_uuid_hex, sql)
