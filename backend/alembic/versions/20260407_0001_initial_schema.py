"""initial schema

Revision ID: 20260407_0001
Revises:
Create Date: 2026-04-07 00:01:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260407_0001"
down_revision = None
branch_labels = None
depends_on = None


item_type_enum = sa.Enum(
    "medication",
    "supply",
    name="item_type_enum",
    native_enum=False,
)
prescription_status_enum = sa.Enum(
    "active",
    "paused",
    "completed",
    "cancelled",
    name="prescription_status_enum",
    native_enum=False,
)
inventory_movement_type_enum = sa.Enum(
    "entry",
    "exit",
    "adjustment",
    name="inventory_movement_type_enum",
    native_enum=False,
)
alert_severity_enum = sa.Enum(
    "info",
    "warning",
    "critical",
    name="alert_severity_enum",
    native_enum=False,
)
alert_status_enum = sa.Enum(
    "open",
    "acknowledged",
    "resolved",
    name="alert_status_enum",
    native_enum=False,
)
notification_channel_enum = sa.Enum(
    "email",
    "whatsapp",
    "internal",
    name="notification_channel_enum",
    native_enum=False,
)
notification_status_enum = sa.Enum(
    "pending",
    "sent",
    "failed",
    name="notification_status_enum",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("care_notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patients")),
    )
    op.create_index(op.f("ix_patients_full_name"), "patients", ["full_name"], unique=False)

    op.create_table(
        "units",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_units")),
        sa.UniqueConstraint("name", name=op.f("uq_units_name")),
        sa.UniqueConstraint("symbol", name=op.f("uq_units_symbol")),
    )

    op.create_table(
        "notification_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("channel", notification_channel_enum, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_contacts")),
    )
    op.create_index(
        op.f("ix_notification_contacts_email"),
        "notification_contacts",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_contacts_phone"),
        "notification_contacts",
        ["phone"],
        unique=False,
    )

    op.create_table(
        "items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("item_type", item_type_enum, nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("minimum_stock", sa.Numeric(precision=14, scale=3), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], name=op.f("fk_items_unit_id_units"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_items")),
    )
    op.create_index(op.f("ix_items_name"), "items", ["name"], unique=False)
    op.create_index(op.f("ix_items_sku"), "items", ["sku"], unique=False)
    op.create_index(op.f("ix_items_unit_id"), "items", ["unit_id"], unique=False)

    op.create_table(
        "prescriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prescribed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dosage_quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("frequency", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            prescription_status_enum,
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name=op.f("fk_prescriptions_item_id_items"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_prescriptions_patient_id_patients"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prescribed_by_user_id"],
            ["users.id"],
            name=op.f("fk_prescriptions_prescribed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["units.id"],
            name=op.f("fk_prescriptions_unit_id_units"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prescriptions")),
    )
    op.create_index(op.f("ix_prescriptions_item_id"), "prescriptions", ["item_id"], unique=False)
    op.create_index(op.f("ix_prescriptions_patient_id"), "prescriptions", ["patient_id"], unique=False)
    op.create_index(
        op.f("ix_prescriptions_prescribed_by_user_id"),
        "prescriptions",
        ["prescribed_by_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_prescriptions_unit_id"), "prescriptions", ["unit_id"], unique=False)

    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prescription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("movement_type", inventory_movement_type_enum, nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_inventory_movements_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name=op.f("fk_inventory_movements_item_id_items"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_inventory_movements_patient_id_patients"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["prescription_id"],
            ["prescriptions.id"],
            name=op.f("fk_inventory_movements_prescription_id_prescriptions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["units.id"],
            name=op.f("fk_inventory_movements_unit_id_units"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_movements")),
    )
    op.create_index(
        op.f("ix_inventory_movements_created_by_user_id"),
        "inventory_movements",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_inventory_movements_item_id"), "inventory_movements", ["item_id"], unique=False)
    op.create_index(
        op.f("ix_inventory_movements_patient_id"),
        "inventory_movements",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_movements_prescription_id"),
        "inventory_movements",
        ["prescription_id"],
        unique=False,
    )
    op.create_index(op.f("ix_inventory_movements_unit_id"), "inventory_movements", ["unit_id"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            alert_severity_enum,
            nullable=False,
            server_default=sa.text("'warning'"),
        ),
        sa.Column(
            "status",
            alert_status_enum,
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["acknowledged_by_user_id"],
            ["users.id"],
            name=op.f("fk_alerts_acknowledged_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name=op.f("fk_alerts_item_id_items"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_alerts_patient_id_patients"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
    )
    op.create_index(op.f("ix_alerts_acknowledged_by_user_id"), "alerts", ["acknowledged_by_user_id"], unique=False)
    op.create_index(op.f("ix_alerts_item_id"), "alerts", ["item_id"], unique=False)
    op.create_index(op.f("ix_alerts_patient_id"), "alerts", ["patient_id"], unique=False)

    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", notification_channel_enum, nullable=False),
        sa.Column(
            "status",
            notification_status_enum,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name=op.f("fk_notification_logs_alert_id_alerts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["notification_contacts.id"],
            name=op.f("fk_notification_logs_contact_id_notification_contacts"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_logs")),
    )
    op.create_index(op.f("ix_notification_logs_alert_id"), "notification_logs", ["alert_id"], unique=False)
    op.create_index(
        op.f("ix_notification_logs_contact_id"),
        "notification_logs",
        ["contact_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_logs_contact_id"), table_name="notification_logs")
    op.drop_index(op.f("ix_notification_logs_alert_id"), table_name="notification_logs")
    op.drop_table("notification_logs")

    op.drop_index(op.f("ix_alerts_patient_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_item_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_acknowledged_by_user_id"), table_name="alerts")
    op.drop_table("alerts")

    op.drop_index(op.f("ix_inventory_movements_unit_id"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_prescription_id"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_patient_id"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_item_id"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_created_by_user_id"), table_name="inventory_movements")
    op.drop_table("inventory_movements")

    op.drop_index(op.f("ix_prescriptions_unit_id"), table_name="prescriptions")
    op.drop_index(op.f("ix_prescriptions_prescribed_by_user_id"), table_name="prescriptions")
    op.drop_index(op.f("ix_prescriptions_patient_id"), table_name="prescriptions")
    op.drop_index(op.f("ix_prescriptions_item_id"), table_name="prescriptions")
    op.drop_table("prescriptions")

    op.drop_index(op.f("ix_items_unit_id"), table_name="items")
    op.drop_index(op.f("ix_items_sku"), table_name="items")
    op.drop_index(op.f("ix_items_name"), table_name="items")
    op.drop_table("items")

    op.drop_index(op.f("ix_notification_contacts_phone"), table_name="notification_contacts")
    op.drop_index(op.f("ix_notification_contacts_email"), table_name="notification_contacts")
    op.drop_table("notification_contacts")

    op.drop_table("units")

    op.drop_index(op.f("ix_patients_full_name"), table_name="patients")
    op.drop_table("patients")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
