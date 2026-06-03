"""overrides audit table

Revision ID: 0002_overrides
Revises: 0001_init
Create Date: 2026-06-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_overrides"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("patient_phone", sa.String(length=64), nullable=False),
        sa.Column("original_priority", sa.String(length=8), nullable=True),
        sa.Column("corrected_priority", sa.String(length=8), nullable=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("receptionist_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_overrides_patient_phone", "overrides", ["patient_phone"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_overrides_patient_phone", table_name="overrides")
    op.drop_table("overrides")
