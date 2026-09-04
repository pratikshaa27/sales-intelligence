from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.rbac import Role


class RBACRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_role_by_name(self, name: str) -> Role | None:
        result = await self.db.execute(
            select(Role).options(joinedload(Role.permissions)).where(Role.name == name)
        )
        return result.unique().scalar_one_or_none()

    async def get_permission_codes_for_role(self, role: Role) -> list[str]:
        return [p.code for p in role.permissions]
