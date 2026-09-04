import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str = "",
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        ip_address: str = "",
        user_agent: str = "",
        metadata: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata=metadata or {},
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_paginated(
        self,
        *,
        organization_id: uuid.UUID,
        action: str | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[AuditLog], int]:
        conditions = [AuditLog.organization_id == organization_id]
        if action:
            conditions.append(AuditLog.action == action)

        total = (
            await self.db.execute(select(func.count()).select_from(AuditLog).where(*conditions))
        ).scalar_one()
        result = await self.db.execute(
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total
