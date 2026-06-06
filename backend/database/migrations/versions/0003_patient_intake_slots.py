"""patient intake slots snapshot

Revision ID: 0003_intake_slots
Revises: 0002_overrides
Create Date: 2026-06-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_intake_slots"
down_revision = "0002_overrides"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column(
            "intake_slots",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "patients",
        sa.Column("slots_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("patients", sa.Column("pending_slot", sa.String(length=64), nullable=True))
    op.add_column("patients", sa.Column("routed_to", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("patients", "routed_to")
    op.drop_column("patients", "pending_slot")
    op.drop_column("patients", "slots_complete")
    op.drop_column("patients", "intake_slots")
