"""per-doctor appointment slots

Revision ID: 0005_appointments
Revises: 0004_clinic_rag
Create Date: 2026-06-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_appointments"
down_revision = "0004_clinic_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("doctor_key", sa.String(length=32), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("guest_code", sa.String(length=16), nullable=True),
        sa.Column("session_phone", sa.String(length=64), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "doctor_key",
            "appointment_date",
            "slot_index",
            name="uq_appointments_doctor_date_slot",
        ),
    )
    op.create_index("ix_appointments_contact_phone", "appointments", ["contact_phone"], unique=False)
    op.create_index("ix_appointments_guest_code", "appointments", ["guest_code"], unique=False)
    op.create_index(
        "ix_appointments_doctor_date",
        "appointments",
        ["doctor_key", "appointment_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_appointments_doctor_date", table_name="appointments")
    op.drop_index("ix_appointments_guest_code", table_name="appointments")
    op.drop_index("ix_appointments_contact_phone", table_name="appointments")
    op.drop_table("appointments")
