import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.company import SourceType


class JobType(StrEnum):
    COMPANY_DISCOVERY = "company_discovery"
    COMPANY_RESEARCH = "company_research"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvidenceCategory(StrEnum):
    OVERVIEW = "overview"
    TECHNOLOGY_STACK = "technology_stack"
    HIRING_SIGNAL = "hiring_signal"
    EXPANSION_SIGNAL = "expansion_signal"
    DIGITAL_TRANSFORMATION_SIGNAL = "digital_transformation_signal"
    SECURITY_SIGNAL = "security_signal"
    BUSINESS_CHALLENGE = "business_challenge"
    OTHER = "other"


class ResearchJob(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "research_jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType, name="job_type", native_enum=False), nullable=False, index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=False),
        default=JobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    input_parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    logs: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    result_summary: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResearchEvidence(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "research_evidence"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    research_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_jobs.id", ondelete="SET NULL"), nullable=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True
    )
    category: Mapped[EvidenceCategory] = mapped_column(
        Enum(EvidenceCategory, name="evidence_category", native_enum=False), nullable=False
    )
    fact_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_title: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type", native_enum=False),
        default=SourceType.WEBSITE,
        nullable=False,
    )
    source_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(default=True, nullable=False)
