import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Principal, require_permission
from app.core.database import get_db
from app.core.exceptions import AppError, NotFoundError
from app.models.research import JobStatus, JobType
from app.repositories.research_repository import ResearchJobRepository
from app.schemas.common import PaginatedData, PaginationMeta, SuccessResponse
from app.schemas.research import ResearchJobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=SuccessResponse[PaginatedData[ResearchJobOut]])
async def list_jobs(
    job_type: JobType | None = Query(None),
    status: JobStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(require_permission("companies.view")),
    db: AsyncSession = Depends(get_db),
):
    repo = ResearchJobRepository(db)
    items, total = await repo.list_paginated(
        organization_id=principal.organization_id,
        job_type=job_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    data = PaginatedData(
        items=[ResearchJobOut.model_validate(j) for j in items],
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total, total_pages=total_pages
        ),
    )
    return SuccessResponse(data=data)


@router.get("/{job_id}", response_model=SuccessResponse[ResearchJobOut])
async def get_job(
    job_id: uuid.UUID,
    principal: Principal = Depends(require_permission("companies.view")),
    db: AsyncSession = Depends(get_db),
):
    repo = ResearchJobRepository(db)
    job = await repo.get_by_id(organization_id=principal.organization_id, job_id=job_id)
    if job is None:
        raise NotFoundError("Job not found")
    return SuccessResponse(data=ResearchJobOut.model_validate(job))


@router.get("/{job_id}/logs", response_model=SuccessResponse[list[str]])
async def get_job_logs(
    job_id: uuid.UUID,
    principal: Principal = Depends(require_permission("companies.view")),
    db: AsyncSession = Depends(get_db),
):
    repo = ResearchJobRepository(db)
    job = await repo.get_by_id(organization_id=principal.organization_id, job_id=job_id)
    if job is None:
        raise NotFoundError("Job not found")
    return SuccessResponse(data=job.logs)


@router.post("/{job_id}/cancel", response_model=SuccessResponse[ResearchJobOut])
async def cancel_job(
    job_id: uuid.UUID,
    principal: Principal = Depends(require_permission("companies.edit")),
    db: AsyncSession = Depends(get_db),
):
    repo = ResearchJobRepository(db)
    job = await repo.get_by_id(organization_id=principal.organization_id, job_id=job_id)
    if job is None:
        raise NotFoundError("Job not found")
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise AppError("CONFLICT", f"Job is already {job.status.value}", 409)

    # Cooperative cancellation: the worker checks this flag between pipeline steps and stops
    # there rather than being killed mid-request, since Celery can't safely interrupt an
    # in-flight HTTP call to an external site or AI provider.
    job.status = JobStatus.CANCELLED
    await db.commit()
    return SuccessResponse(
        data=ResearchJobOut.model_validate(job), message="Job cancellation requested"
    )
