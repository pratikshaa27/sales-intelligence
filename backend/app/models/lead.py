import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class LeadStatus(StrEnum):
    NEW = "new"
    RESEARCHING = "researching"
    QUALIFIED = "qualified"
    ASSIGNED = "assigned"
    CONTACTED = "contacted"
    MEETING_SCHEDULED = "meeting_scheduled"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"
    DISQUALIFIED = "disqualified"
    ARCHIVED = "archived"


class LeadPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActivityType(StrEnum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    ASSIGNED = "assigned"
    NOTE_ADDED = "note_added"
    SCORE_RECALCULATED = "score_recalculated"
    BRIEF_GENERATED = "brief_generated"
    RESEARCH_RERUN = "research_rerun"
    OTHER = "other"


class Lead(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "leads"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(255), default="manual", nullable=False)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status", native_enum=False),
        default=LeadStatus.NEW,
        nullable=False,
        index=True,
    )
    priority: Mapped[LeadPriority] = mapped_column(
        Enum(LeadPriority, name="lead_priority", native_enum=False),
        default=LeadPriority.LOW,
        nullable=False,
        index=True,
    )

    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fit_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    need_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    authority_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timing_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    data_confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    research_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    next_action: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    scores: Mapped[list["LeadScore"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )
    briefs: Mapped[list["SalesBrief"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )
    notes: Mapped[list["LeadNote"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )
    activities: Mapped[list["LeadActivity"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )


class LeadScore(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "lead_scores"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    fit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    need_score: Mapped[int] = mapped_column(Integer, nullable=False)
    authority_score: Mapped[int] = mapped_column(Integer, nullable=False)
    timing_score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    missing_information: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    lead: Mapped["Lead"] = relationship(back_populates="scores")


class SalesBrief(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "sales_briefs"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    company_overview: Mapped[str] = mapped_column(Text, default="", nullable=False)
    why_relevant: Mapped[str] = mapped_column(Text, default="", nullable=False)
    matched_product_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    possible_business_problem: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_summary: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    relevant_decision_maker: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    suggested_opener: Mapped[str] = mapped_column(Text, default="", nullable=False)
    discovery_questions: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    recommended_next_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    missing_information: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ai_provider: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    lead: Mapped["Lead"] = relationship(back_populates="briefs")


class LeadNote(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "lead_notes"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    lead: Mapped["Lead"] = relationship(back_populates="notes")


class LeadActivity(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "lead_activities"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activity_type", native_enum=False), nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    lead: Mapped["Lead"] = relationship(back_populates="activities")
