"""Imports all SQLAlchemy models so Alembic can discover metadata."""

from app.modules.auth.models import User
from app.modules.internal_alerts.models import Alert
from app.modules.inventory.models import InventoryMovement
from app.modules.items.models import Item
from app.modules.measurement_units.models import Unit
from app.modules.notifications.models import NotificationContact, NotificationLog
from app.modules.patients.models import Patient
from app.modules.prescriptions.models import Prescription

__all__ = [
    "Alert",
    "InventoryMovement",
    "Item",
    "NotificationContact",
    "NotificationLog",
    "Patient",
    "Prescription",
    "Unit",
    "User",
]
