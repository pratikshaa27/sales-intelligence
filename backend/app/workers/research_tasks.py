import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.provider import CompletionProviderError, get_completion_provider
from app.ai.schemas import ExtractedCompanyProfile
from app.core.config import get_settings
from app.core.ssrf_protection import SSRFError
from app.core.utils import normalize_domain
from app.models.company import Company, ResearchStatus, SourceType
from app.models.research import EvidenceCategory, JobStatus, ResearchJob
from app.models.security_event import SecurityEventSeverity, SecurityEventType
from app.repositories.company_repository import CompanyRepository, CompanySourceRepository
from app.repositories.research_repository import ResearchEvidenceRepository
from app.repositories.security_event_repository import SecurityEventRepository
from app.research.discovery_provider import get_discovery_provider
from app.research.website_fetcher import WebsiteFetchError, fetch_website_text
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _append_progress(
    db, job: ResearchJob, *, percentage: int, step: str, log_line: str
) -> None:
    job.progress_percentage = percentage
    job.current_step = step
    job.logs = [*job.logs, log_line]
    await db.commit()


async def _is_cancelled(db, job_id: uuid.UUID) -> bool:
    job = await db.get(ResearchJob, job_id)
    return job is not None and job.status == JobStatus.CANCELLED


async def _fail_job(db, job: ResearchJob, message: str) -> None:
    job.status = JobStatus.FAILED
    job.error_message = message
    job.completed_at = datetime.now(UTC)
    job.logs = [*job.logs, f"Failed: {message}"]
    await db.commit()


def _merge_company_profile(company: Company, profile: ExtractedCompanyProfile) -> None:
    """Merge AI-extracted findings into the company record without discarding anything a human
    already entered: union list fields, only fill business_description if it was empty, and take
    the higher confidence score rather than overwriting a manually-set one downward."""
    company.technology_stack = sorted(set(company.technology_stack) | set(profile.technology_stack))
    company.business_challenges = sorted(
        set(company.business_challenges) | set(profile.business_challenges)
    )
    new_signals = set(profile.hiring_signals) | set(profile.expansion_signals)
    company.public_signals = sorted(set(company.public_signals) | new_signals)
    if not company.business_description and profile.overview:
        company.business_description = profile.overview
    company.confidence_score = max(company.confidence_score, profile.confidence)


async def _extract_profile_with_retries(
    db, job: ResearchJob, *, company_name: str, webpage_text: str, max_attempts: int = 3
) -> ExtractedCompanyProfile | None:
    provider = get_completion_provider()
    for attempt in range(1, max_attempts + 1):
        try:
            return await provider.extract_company_profile(
                company_name=company_name, webpage_text=webpage_text
            )
        except CompletionProviderError as exc:
            job.logs = [*job.logs, f"Extraction attempt {attempt} failed: {exc}"]
            await db.commit()
            if attempt < max_attempts:
                await asyncio.sleep(2**attempt)
    return None


async def _run_company_research_async(job_id: str) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            job = await db.get(ResearchJob, uuid.UUID(job_id))
            if job is None:
                logger.warning("research_job_not_found", extra={"job_id": job_id})
                return
            if job.status == JobStatus.CANCELLED:
                return

            try:
                companies = CompanyRepository(db)
                company_id = uuid.UUID(job.input_parameters["company_id"])
                company = await companies.get_by_id(
                    organization_id=job.organization_id, company_id=company_id
                )
                if company is None:
                    await _fail_job(db, job, "Company no longer exists")
                    return

                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(UTC)
                await _append_progress(
                    db,
                    job,
                    percentage=10,
                    step="Fetching website",
                    log_line=f"Fetching {company.website}",
                )

                try:
                    page = await fetch_website_text(company.website)
                except WebsiteFetchError as exc:
                    if isinstance(exc.__cause__, SSRFError):
                        await SecurityEventRepository(db).log(
                            event_type=SecurityEventType.SSRF_BLOCKED,
                            severity=SecurityEventSeverity.HIGH,
                            description=f"Blocked unsafe research fetch target: {exc}",
                            organization_id=job.organization_id,
                            user_id=job.user_id,
                            metadata={"company_id": str(company.id), "website": company.website},
                        )
                    await _fail_job(db, job, f"Could not fetch website: {exc}")
                    return

                if await _is_cancelled(db, job.id):
                    return

                await _append_progress(
                    db,
                    job,
                    percentage=50,
                    step="Extracting structured profile",
                    log_line="Running AI extraction over fetched content",
                )

                profile = await _extract_profile_with_retries(
                    db, job, company_name=company.name, webpage_text=page.text
                )
                if profile is None:
                    await _fail_job(db, job, "AI extraction failed after multiple attempts")
                    return

                if await _is_cancelled(db, job.id):
                    return

                retrieved_at = datetime.now(UTC)
                evidence_repo = ResearchEvidenceRepository(db)
                facts: list[tuple[EvidenceCategory, str]] = []
                if profile.overview:
                    facts.append((EvidenceCategory.OVERVIEW, profile.overview))
                facts += [(EvidenceCategory.TECHNOLOGY_STACK, i) for i in profile.technology_stack]
                facts += [(EvidenceCategory.HIRING_SIGNAL, i) for i in profile.hiring_signals]
                facts += [(EvidenceCategory.EXPANSION_SIGNAL, i) for i in profile.expansion_signals]
                facts += [
                    (EvidenceCategory.BUSINESS_CHALLENGE, i) for i in profile.business_challenges
                ]

                for category, fact_text in facts:
                    await evidence_repo.create(
                        organization_id=job.organization_id,
                        research_job_id=job.id,
                        company_id=company.id,
                        category=category,
                        fact_text=fact_text,
                        source_url=page.final_url,
                        source_title=page.title,
                        source_type=SourceType.WEBSITE,
                        retrieved_at=retrieved_at,
                        confidence=profile.confidence,
                        is_ai_generated=True,
                    )

                sources = CompanySourceRepository(db)
                await sources.create(
                    company_id=company.id,
                    organization_id=job.organization_id,
                    url=page.final_url,
                    title=page.title or company.name,
                    source_type=SourceType.WEBSITE,
                    added_by=job.user_id,
                )

                _merge_company_profile(company, profile)
                company.research_status = ResearchStatus.RESEARCHED

                job.status = JobStatus.COMPLETED
                job.progress_percentage = 100
                job.current_step = "Done"
                job.completed_at = datetime.now(UTC)
                job.result_summary = {
                    "evidence_created": len(facts),
                    "confidence": profile.confidence,
                    "provider": get_completion_provider().name,
                }
                job.logs = [*job.logs, f"Completed: {len(facts)} evidence items saved"]
                await db.commit()
            except Exception as exc:  # noqa: BLE001 - safety net so a job never sticks at RUNNING
                logger.exception("company_research_task_crashed", extra={"job_id": job_id})
                await _fail_job(db, job, f"Unexpected error: {exc}")
                raise
    finally:
        await engine.dispose()


async def _run_company_discovery_async(job_id: str) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            job = await db.get(ResearchJob, uuid.UUID(job_id))
            if job is None:
                logger.warning("research_job_not_found", extra={"job_id": job_id})
                return
            if job.status == JobStatus.CANCELLED:
                return

            try:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(UTC)
                await _append_progress(
                    db,
                    job,
                    percentage=20,
                    step="Querying discovery provider",
                    log_line="Starting discovery",
                )

                provider = get_discovery_provider()
                params = job.input_parameters
                candidates = await provider.discover_companies(
                    industry=params.get("industry", ""),
                    location=params.get("location", ""),
                    company_size=params.get("company_size", ""),
                    keywords=params.get("keywords", []),
                    limit=params.get("number_of_companies", 5),
                )

                if await _is_cancelled(db, job.id):
                    return

                # Discovery only ever proposes candidates for human review (spec §6 step
                # 11/12) — it never creates Company rows itself, so mock/placeholder data can
                # never end up silently mixed into the organization's real company list.
                companies = CompanyRepository(db)
                candidate_dicts = []
                for candidate in candidates:
                    domain = normalize_domain(candidate.website)
                    existing = (
                        await companies.get_by_domain(
                            organization_id=job.organization_id, domain=domain
                        )
                        if domain
                        else None
                    )
                    candidate_dicts.append(
                        {
                            **candidate.model_dump(),
                            "domain": domain,
                            "already_exists": existing is not None,
                        }
                    )

                job.status = JobStatus.COMPLETED
                job.progress_percentage = 100
                job.current_step = "Done"
                job.completed_at = datetime.now(UTC)
                job.result_summary = {
                    "candidates": candidate_dicts,
                    "is_mock_data": provider.is_mock,
                    "provider": provider.name,
                }
                job.logs = [*job.logs, f"Completed: {len(candidate_dicts)} candidates found"]
                await db.commit()
            except Exception as exc:  # noqa: BLE001 - safety net so a job never sticks at RUNNING
                logger.exception("company_discovery_task_crashed", extra={"job_id": job_id})
                await _fail_job(db, job, f"Unexpected error: {exc}")
                raise
    finally:
        await engine.dispose()


@celery_app.task(name="research.run_company_research", bind=True)
def run_company_research(self, job_id: str) -> str:
    asyncio.run(_run_company_research_async(job_id))
    return "completed"


@celery_app.task(name="research.run_company_discovery", bind=True)
def run_company_discovery(self, job_id: str) -> str:
    asyncio.run(_run_company_discovery_async(job_id))
    return "completed"
