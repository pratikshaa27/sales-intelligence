import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.contact import Contact


class ResearchStatus(StrEnum):
    NOT_RESEARCHED = "not_researched"
    RESEARCHING = "researching"
    RESEARCHED = "researched"
    FAILED = "failed"


class SourceType(StrEnum):
    WEBSITE = "website"
    DIRECTORY = "directory"
    NEWS = "news"
    JOB_POSTING = "job_posting"
    SOCIAL_PROFILE = "social_profile"
    OTHER = "other"


class Company(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    industry: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    locations: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    company_size: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    revenue_range: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    business_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    technology_stack: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    business_challenges: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    public_signals: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    research_status: Mapped[ResearchStatus] = mapped_column(
        Enum(ResearchStatus, name="research_status", native_enum=False),
        default=ResearchStatus.NOT_RESEARCHED,
        nullable=False,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    sources: Mapped[list["CompanySource"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class CompanySource(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "company_sources"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    title: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type", native_enum=False),
        default=SourceType.OTHER,
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    added_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    company: Mapped["Company"] = relationship(back_populates="sources")
