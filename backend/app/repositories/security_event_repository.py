import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security_event import SecurityEvent, SecurityEventSeverity, SecurityEventType


class SecurityEventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        *,
        event_type: SecurityEventType,
        description: str,
        severity: SecurityEventSeverity = SecurityEventSeverity.LOW,
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        ip_address: str = "",
        user_agent: str = "",
        metadata: dict | None = None,
    ) -> SecurityEvent:
        entry = SecurityEvent(
            organization_id=organization_id,
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            description=description,
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
        event_type: SecurityEventType | None,
        severity: SecurityEventSeverity | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[SecurityEvent], int]:
        conditions = [SecurityEvent.organization_id == organization_id]
        if event_type:
            conditions.append(SecurityEvent.event_type == event_type)
        if severity:
            conditions.append(SecurityEvent.severity == severity)

        total = (
            await self.db.execute(
                select(func.count()).select_from(SecurityEvent).where(*conditions)
            )
        ).scalar_one()
        result = await self.db.execute(
            select(SecurityEvent)
            .where(*conditions)
            .order_by(SecurityEvent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total
