import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.research import JobStatus, JobType, ResearchEvidence, ResearchJob
from app.repositories.audit_repository import AuditRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.research_repository import ResearchEvidenceRepository, ResearchJobRepository
from app.schemas.research import DiscoverCompaniesRequest


class ResearchJobService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.jobs = ResearchJobRepository(db)
        self.companies = CompanyRepository(db)
        self.evidence = ResearchEvidenceRepository(db)
        self.audit = AuditRepository(db)

    async def start_company_research(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> ResearchJob:
        # Imported lazily so the web process doesn't need Celery's broker wiring unless a
        # research job is actually queued (mirrors ProductService.reindex).
        from app.workers.research_tasks import run_company_research

        company = await self.companies.get_by_id(
            organization_id=organization_id, company_id=company_id
        )
        if company is None:
            raise AppError("NOT_FOUND", "Company not found", 404)

        job = await self.jobs.create(
            organization_id=organization_id,
            user_id=user_id,
            job_type=JobType.COMPANY_RESEARCH,
            input_parameters={"company_id": str(company_id)},
        )
        await self.audit.log(
            action="company.research_requested",
            resource_type="research_job",
            resource_id=str(job.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()

        await self._enqueue(run_company_research, job)
        return job

    async def start_company_discovery(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, body: DiscoverCompaniesRequest
    ) -> ResearchJob:
        from app.workers.research_tasks import run_company_discovery

        job = await self.jobs.create(
            organization_id=organization_id,
            user_id=user_id,
            job_type=JobType.COMPANY_DISCOVERY,
            input_parameters=body.model_dump(),
        )
        await self.audit.log(
            action="company.discovery_requested",
            resource_type="research_job",
            resource_id=str(job.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()

        await self._enqueue(run_company_discovery, job)
        return job

    async def _enqueue(self, task, job: ResearchJob) -> None:
        try:
            task.delay(str(job.id))
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error_message = "Could not queue the job (broker unavailable)"
            await self.db.commit()
            raise AppError(
                "JOB_QUEUE_UNAVAILABLE", "Could not queue the research job; try again shortly", 503
            ) from exc

    async def list_evidence_for_company(
        self, *, organization_id: uuid.UUID, company_id: uuid.UUID
    ) -> list[ResearchEvidence]:
        company = await self.companies.get_by_id(
            organization_id=organization_id, company_id=company_id
        )
        if company is None:
            raise AppError("NOT_FOUND", "Company not found", 404)
        return list(
            await self.evidence.list_for_company(
                organization_id=organization_id, company_id=company_id
            )
        )
