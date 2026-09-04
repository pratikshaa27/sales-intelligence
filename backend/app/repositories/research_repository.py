import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import JobStatus, JobType, ResearchEvidence, ResearchJob


class ResearchJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, *, organization_id: uuid.UUID, job_id: uuid.UUID
    ) -> ResearchJob | None:
        result = await self.db.execute(
            select(ResearchJob).where(
                ResearchJob.id == job_id, ResearchJob.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields) -> ResearchJob:
        job = ResearchJob(**fields)
        self.db.add(job)
        await self.db.flush()
        return job

    async def list_paginated(
        self,
        *,
        organization_id: uuid.UUID,
        job_type: JobType | None,
        status: JobStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[ResearchJob], int]:
        conditions = [ResearchJob.organization_id == organization_id]
        if job_type:
            conditions.append(ResearchJob.job_type == job_type)
        if status:
            conditions.append(ResearchJob.status == status)

        total = (
            await self.db.execute(select(func.count()).select_from(ResearchJob).where(*conditions))
        ).scalar_one()
        result = await self.db.execute(
            select(ResearchJob)
            .where(*conditions)
            .order_by(ResearchJob.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total


class ResearchEvidenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **fields) -> ResearchEvidence:
        evidence = ResearchEvidence(**fields)
        self.db.add(evidence)
        await self.db.flush()
        return evidence

    async def list_for_company(
        self, *, organization_id: uuid.UUID, company_id: uuid.UUID
    ) -> Sequence[ResearchEvidence]:
        result = await self.db.execute(
            select(ResearchEvidence)
            .where(
                ResearchEvidence.organization_id == organization_id,
                ResearchEvidence.company_id == company_id,
            )
            .order_by(ResearchEvidence.retrieved_at.desc())
        )
        return result.scalars().all()
