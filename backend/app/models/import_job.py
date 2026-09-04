import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class ImportEntityType(StrEnum):
    COMPANY = "company"
    CONTACT = "contact"
    PRODUCT = "product"
    LEAD = "lead"


class ImportJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportJob(UUIDPKMixin, TimestampMixin, Base):
    """Background CSV import (spec §17). Mirrors ResearchJob's progress/log-tracking shape but
    lives in its own table rather than reusing research_jobs — import authorization is scoped to
    each target entity's own `.create` permission (companies.create, leads.create, etc.), which a
    shared research-jobs-flavoured permission gate couldn't express correctly."""

    __tablename__ = "import_jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    entity_type: Mapped[ImportEntityType] = mapped_column(
        Enum(ImportEntityType, name="import_entity_type", native_enum=False),
        nullable=False,
        index=True,
    )
    status: Mapped[ImportJobStatus] = mapped_column(
        Enum(ImportJobStatus, name="import_job_status", native_enum=False),
        default=ImportJobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    logs: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    row_errors: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
