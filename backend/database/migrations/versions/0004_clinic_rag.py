"""clinic knowledge chunks with pgvector embeddings

Revision ID: 0004_clinic_rag
Revises: 0003_intake_slots
Create Date: 2026-06-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_clinic_rag"
down_revision = "0003_intake_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "clinic_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("chunk_key", sa.String(length=128), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_clinic_chunks_chunk_key", "clinic_chunks", ["chunk_key"], unique=True)
    op.execute(
        "ALTER TABLE clinic_chunks ADD COLUMN embedding vector(1536)"
    )


def downgrade() -> None:
    op.drop_index("ix_clinic_chunks_chunk_key", table_name="clinic_chunks")
    op.drop_table("clinic_chunks")
