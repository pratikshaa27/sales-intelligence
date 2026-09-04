import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class SecurityEventType(StrEnum):
    LOGIN_FAILED = "login_failed"
    ACCOUNT_LOCKED = "account_locked"
    PERMISSION_DENIED = "permission_denied"
    SSRF_BLOCKED = "ssrf_blocked"
    CSRF_REJECTED = "csrf_rejected"


class SecurityEventSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEvent(UUIDPKMixin, TimestampMixin, Base):
    """A distinct security-relevant event log (spec §11/§19), separate from the general
    `audit_logs` action trail — narrower and higher-signal: only events that represent a
    possible attack, policy violation, or abuse attempt land here (failed logins, lockouts,
    permission denials, blocked SSRF attempts), so a reviewer scanning this table doesn't have
    to wade through routine CRUD activity to find what matters."""

    __tablename__ = "security_events"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[SecurityEventType] = mapped_column(
        Enum(SecurityEventType, name="security_event_type", native_enum=False),
        nullable=False,
        index=True,
    )
    severity: Mapped[SecurityEventSeverity] = mapped_column(
        Enum(SecurityEventSeverity, name="security_event_severity", native_enum=False),
        default=SecurityEventSeverity.LOW,
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
