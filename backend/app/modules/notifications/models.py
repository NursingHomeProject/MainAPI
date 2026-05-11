from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID as UUIDValue

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.internal_alerts.models import Alert


class NotificationChannel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    INTERNAL = "internal"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class NotificationContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_contacts"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        SqlEnum(NotificationChannel, name="notification_channel_enum", native_enum=False),
        nullable=False,
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    notification_logs: Mapped[list["NotificationLog"]] = relationship(back_populates="contact")


class NotificationLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_logs"

    alert_id: Mapped[UUIDValue] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[UUIDValue | None] = mapped_column(
        ForeignKey("notification_contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        SqlEnum(NotificationChannel, name="notification_channel_enum", native_enum=False),
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        SqlEnum(NotificationStatus, name="notification_status_enum", native_enum=False),
        nullable=False,
        default=NotificationStatus.PENDING,
        server_default=NotificationStatus.PENDING.value,
    )
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    alert: Mapped["Alert"] = relationship(back_populates="notification_logs")
    contact: Mapped["NotificationContact | None"] = relationship(back_populates="notification_logs")
