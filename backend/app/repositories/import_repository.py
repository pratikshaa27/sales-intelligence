import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_job import ImportEntityType, ImportJob, ImportJobStatus


class ImportJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, *, organization_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob | None:
        result = await self.db.execute(
            select(ImportJob).where(
                ImportJob.id == job_id, ImportJob.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields) -> ImportJob:
        job = ImportJob(**fields)
        self.db.add(job)
        await self.db.flush()
        return job

    async def list_paginated(
        self,
        *,
        organization_id: uuid.UUID,
        entity_type: ImportEntityType | None,
        status: ImportJobStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[ImportJob], int]:
        conditions = [ImportJob.organization_id == organization_id]
        if entity_type:
            conditions.append(ImportJob.entity_type == entity_type)
        if status:
            conditions.append(ImportJob.status == status)

        total = (
            await self.db.execute(select(func.count()).select_from(ImportJob).where(*conditions))
        ).scalar_one()
        result = await self.db.execute(
            select(ImportJob)
            .where(*conditions)
            .order_by(ImportJob.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total
