import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.rbac import Role
    from app.models.user import User


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    INVITED = "invited"


class Organization(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[OrganizationStatus] = mapped_column(
        Enum(OrganizationStatus, name="organization_status", native_enum=False),
        default=OrganizationStatus.ACTIVE,
        nullable=False,
    )
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    members: Mapped[list["OrganizationMember"]] = relationship(back_populates="organization")


class OrganizationMember(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member_org_user"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False
    )
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, name="membership_status", native_enum=False),
        default=MembershipStatus.ACTIVE,
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
    role: Mapped["Role"] = relationship()
