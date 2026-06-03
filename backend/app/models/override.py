from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Override(Base):
    __tablename__ = "overrides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_phone: Mapped[str] = mapped_column(String(64), index=True)
    original_priority: Mapped[str | None] = mapped_column(String(8), nullable=True)
    corrected_priority: Mapped[str | None] = mapped_column(String(8), nullable=True)
    action: Mapped[str] = mapped_column(String(16))
    receptionist_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
