import uuid
from collections.abc import Sequence

from sqlalchemy import Row, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.organization import MembershipStatus, Organization, OrganizationMember
from app.models.rbac import Role
from app.models.user import User


class OrganizationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        return await self.db.get(Organization, org_id)

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.db.execute(select(Organization).where(Organization.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, *, name: str, slug: str) -> Organization:
        org = Organization(name=name, slug=slug)
        self.db.add(org)
        await self.db.flush()
        return org

    async def add_member(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        status: MembershipStatus = MembershipStatus.ACTIVE,
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=organization_id, user_id=user_id, role_id=role_id, status=status
        )
        self.db.add(member)
        await self.db.flush()
        return member

    async def get_membership(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationMember | None:
        result = await self.db.execute(
            select(OrganizationMember)
            .options(joinedload(OrganizationMember.role).joinedload(Role.permissions))
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def list_members(
        self, *, organization_id: uuid.UUID
    ) -> Sequence[Row[tuple[OrganizationMember, User]]]:
        result = await self.db.execute(
            select(OrganizationMember, User)
            .join(User, User.id == OrganizationMember.user_id)
            .options(joinedload(OrganizationMember.role))
            .where(OrganizationMember.organization_id == organization_id)
        )
        return result.all()
