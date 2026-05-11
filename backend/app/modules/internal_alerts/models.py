from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID as UUIDValue

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.items.models import Item
    from app.modules.notifications.models import NotificationLog
    from app.modules.patients.models import Patient


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    item_id: Mapped[UUIDValue | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    patient_id: Mapped[UUIDValue | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolved_by_user_id: Mapped[UUIDValue | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        SqlEnum(AlertSeverity, name="alert_severity_enum", native_enum=False),
        nullable=False,
        default=AlertSeverity.WARNING,
        server_default=AlertSeverity.WARNING.value,
    )
    status: Mapped[AlertStatus] = mapped_column(
        SqlEnum(AlertStatus, name="alert_status_enum", native_enum=False),
        nullable=False,
        default=AlertStatus.OPEN,
        server_default=AlertStatus.OPEN.value,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    item: Mapped["Item | None"] = relationship(back_populates="alerts")
    patient: Mapped["Patient | None"] = relationship(back_populates="alerts")
    resolved_by: Mapped["User | None"] = relationship(back_populates="resolved_alerts")
    notification_logs: Mapped[list["NotificationLog"]] = relationship(back_populates="alert")
