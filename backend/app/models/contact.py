import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.company import SourceType

if TYPE_CHECKING:
    from app.models.company import Company


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"


class Contact(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "contacts"

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

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    department: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    seniority: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    role_relevance: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    # Only public, professionally-sourced business contact details belong here (spec §4.6):
    # no personal email/phone, no private contact info.
    profile_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    business_email: Mapped[str] = mapped_column(String(320), default="", nullable=False)
    business_phone: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status", native_enum=False),
        default=VerificationStatus.UNVERIFIED,
        nullable=False,
    )
    confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    company: Mapped["Company"] = relationship(back_populates="contacts")
    sources: Mapped[list["ContactSource"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan"
    )


class ContactSource(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "contact_sources"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
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

    contact: Mapped["Contact"] = relationship(back_populates="sources")
