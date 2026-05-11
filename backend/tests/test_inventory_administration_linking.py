from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
import unittest
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.modules.inventory.models import InventoryMovementType
from app.modules.inventory.schemas import InventoryMovementCreate
from app.modules.inventory.services import (
    _resolve_prescription_id_for_administration,
    validate_inventory_relationships,
)


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _FakeSession:
    def __init__(self, prescriptions):
        self._prescriptions = prescriptions

    def scalars(self, statement):
        return _ScalarResult(self._prescriptions)


class InventoryAdministrationLinkingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project_timezone = ZoneInfo("America/Sao_Paulo")
        self.patient_id = uuid4()
        self.item_id = uuid4()
        self.prescription_id = uuid4()

    def test_occurred_at_without_timezone_is_normalized(self) -> None:
        payload = InventoryMovementCreate(
            item_id=self.item_id,
            movement_type=InventoryMovementType.ADMINISTRATION,
            quantity=Decimal("1"),
            patient_id=self.patient_id,
            occurred_at=datetime(2026, 4, 12, 8, 0),
        )

        self.assertIsNotNone(payload.occurred_at)
        self.assertEqual(
            payload.occurred_at.tzinfo,
            self.project_timezone,
        )

    def test_resolve_prescription_for_administration_returns_unique_match(self) -> None:
        prescription = SimpleNamespace(
            id=self.prescription_id,
            patient_id=self.patient_id,
            item_id=self.item_id,
            is_active=True,
            start_date=date(2026, 4, 1),
            end_date=None,
            created_at=datetime(2026, 4, 1, 8, 0, tzinfo=self.project_timezone),
        )
        fake_db = _FakeSession([prescription])

        resolved_prescription_id = _resolve_prescription_id_for_administration(
            fake_db,
            patient_id=self.patient_id,
            item_id=self.item_id,
            occurred_at=datetime(2026, 4, 12, 9, 0, tzinfo=self.project_timezone),
        )

        self.assertEqual(resolved_prescription_id, self.prescription_id)

    def test_resolve_prescription_for_administration_returns_none_when_ambiguous(self) -> None:
        first_prescription = SimpleNamespace(
            id=uuid4(),
            patient_id=self.patient_id,
            item_id=self.item_id,
            is_active=True,
            start_date=date(2026, 4, 1),
            end_date=None,
            created_at=datetime(2026, 4, 1, 8, 0, tzinfo=self.project_timezone),
        )
        second_prescription = SimpleNamespace(
            id=uuid4(),
            patient_id=self.patient_id,
            item_id=self.item_id,
            is_active=True,
            start_date=date(2026, 4, 2),
            end_date=None,
            created_at=datetime(2026, 4, 2, 8, 0, tzinfo=self.project_timezone),
        )
        fake_db = _FakeSession([first_prescription, second_prescription])

        resolved_prescription_id = _resolve_prescription_id_for_administration(
            fake_db,
            patient_id=self.patient_id,
            item_id=self.item_id,
            occurred_at=datetime(2026, 4, 12, 9, 0, tzinfo=self.project_timezone),
        )

        self.assertIsNone(resolved_prescription_id)

