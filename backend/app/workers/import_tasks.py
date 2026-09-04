import asyncio
import csv
import io
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.storage import get_file_storage
from app.core.utils import normalize_domain
from app.models.import_job import ImportEntityType, ImportJob, ImportJobStatus
from app.repositories.company_repository import CompanyRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.company import CreateCompanyRequest
from app.schemas.contact import CreateContactRequest
from app.schemas.lead import CreateLeadRequest
from app.schemas.product import CreateProductRequest
from app.services.company_service import CompanyService
from app.services.contact_service import ContactService
from app.services.import_mapping import parse_row
from app.services.lead_service import LeadService
from app.services.product_service import ProductService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

MAX_STORED_ROW_ERRORS = 200


class DuplicateRowError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


async def _append_progress(
    db, job: ImportJob, *, percentage: int, step: str, log_line: str
) -> None:
    job.progress_percentage = percentage
    job.current_step = step
    job.logs = [*job.logs, log_line]
    await db.commit()


async def _fail_job(db, job: ImportJob, message: str) -> None:
    job.status = ImportJobStatus.FAILED
    job.error_message = message
    job.completed_at = datetime.now(UTC)
    job.logs = [*job.logs, f"Failed: {message}"]
    await db.commit()


async def _import_company_row(
    db, *, organization_id: uuid.UUID, user_id: uuid.UUID, values: dict
) -> None:
    service = CompanyService(db)
    body = CreateCompanyRequest(**values)
    await service.create(organization_id=organization_id, user_id=user_id, body=body)


async def _import_contact_row(
    db, *, organization_id: uuid.UUID, user_id: uuid.UUID, values: dict
) -> None:
    website = values.pop("company_website", "")
    domain = normalize_domain(website)
    company = (
        await CompanyRepository(db).get_by_domain(organization_id=organization_id, domain=domain)
        if domain
        else None
    )
    if company is None:
        raise AppError("VALIDATION_ERROR", f"No company found for website '{website}'", 422)

    contacts = ContactRepository(db)
    existing = await contacts.find_duplicate(
        organization_id=organization_id,
        company_id=company.id,
        full_name=values.get("full_name", ""),
        business_email=values.get("business_email", ""),
    )
    if existing:
        raise DuplicateRowError("Duplicate contact (matched by email or name at this company)")

    service = ContactService(db)
    body = CreateContactRequest(company_id=company.id, **values)
    await service.create(organization_id=organization_id, user_id=user_id, body=body)


async def _import_product_row(
    db, *, organization_id: uuid.UUID, user_id: uuid.UUID, values: dict
) -> None:
    service = ProductService(db)
    body = CreateProductRequest(**values)
    await service.create(organization_id=organization_id, user_id=user_id, body=body)


async def _import_lead_row(
    db, *, organization_id: uuid.UUID, user_id: uuid.UUID, values: dict
) -> None:
    website = values.pop("company_website", "")
    domain = normalize_domain(website)
    company = (
        await CompanyRepository(db).get_by_domain(organization_id=organization_id, domain=domain)
        if domain
        else None
    )
    if company is None:
        raise AppError("VALIDATION_ERROR", f"No company found for website '{website}'", 422)

    code = values.pop("product_code", "")
    product = await ProductRepository(db).get_by_code(organization_id=organization_id, code=code)
    if product is None:
        raise AppError("VALIDATION_ERROR", f"No product found for code '{code}'", 422)

    contact_id = None
    contact_email = values.pop("contact_email", "")
    if contact_email:
        contact = await ContactRepository(db).find_duplicate(
            organization_id=organization_id,
            company_id=company.id,
            full_name="",
            business_email=contact_email,
        )
        if contact is None:
            raise AppError(
                "VALIDATION_ERROR",
                f"No contact found with email '{contact_email}' at that company",
                422,
            )
        contact_id = contact.id

    existing_lead = await LeadRepository(db).find_active_for_company_and_product(
        organization_id=organization_id, company_id=company.id, product_id=product.id
    )
    if existing_lead:
        raise DuplicateRowError("An open lead already exists for this company/product pairing")

    service = LeadService(db)
    body = CreateLeadRequest(
        company_id=company.id, product_id=product.id, contact_id=contact_id, **values
    )
    await service.create(organization_id=organization_id, user_id=user_id, body=body)


ROW_IMPORTERS = {
    ImportEntityType.COMPANY: _import_company_row,
    ImportEntityType.CONTACT: _import_contact_row,
    ImportEntityType.PRODUCT: _import_product_row,
    ImportEntityType.LEAD: _import_lead_row,
}


async def _process_row(
    db, job: ImportJob, user_id: uuid.UUID, row_number: int, raw_row: dict
) -> tuple[str, str | None]:
    """Returns ("created" | "skipped" | "error", reason_or_None)."""
    job_id_str = str(job.id)  # captured up front — unsafe to read after a rollback below expires it
    parsed = parse_row(job.entity_type.value, row_number, raw_row)
    if not parsed.is_valid:
        return "error", "; ".join(parsed.errors)

    values = {k: v for k, v in parsed.values.items() if v is not None}
    importer = ROW_IMPORTERS[job.entity_type]
    organization_id = job.organization_id
    try:
        await importer(db, organization_id=organization_id, user_id=user_id, values=values)
        return "created", None
    except DuplicateRowError as exc:
        await db.rollback()
        return "skipped", exc.reason
    except AppError as exc:
        await db.rollback()
        if exc.code == "CONFLICT":
            return "skipped", exc.message
        return "error", exc.message
    except Exception as exc:  # noqa: BLE001 - a bad row must not sink the whole import
        await db.rollback()
        logger.exception("import_row_crashed", extra={"job_id": job_id_str, "row": row_number})
        return "error", f"Unexpected error: {exc}"


async def _run_import_async(job_id: str) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    job_uuid = uuid.UUID(job_id)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            job = await db.get(ImportJob, job_uuid)
            if job is None:
                logger.warning("import_job_not_found", extra={"job_id": job_id})
                return
            if job.status == ImportJobStatus.CANCELLED:
                return
            if job.user_id is None:
                await _fail_job(db, job, "The user who requested this import no longer exists")
                return
            requesting_user_id: uuid.UUID = job.user_id

            try:
                storage = get_file_storage()
                content = await storage.read(job.storage_key)
                text = content.decode("utf-8-sig")
                rows = list(csv.DictReader(io.StringIO(text)))

                job.status = ImportJobStatus.RUNNING
                job.started_at = datetime.now(UTC)
                job.total_rows = len(rows)
                await _append_progress(
                    db,
                    job,
                    percentage=0,
                    step="Importing rows",
                    log_line=f"Parsed {len(rows)} data row(s) from {job.file_name}",
                )

                row_errors: list[dict] = []
                created = skipped = errored = 0

                for i, raw_row in enumerate(rows, start=2):  # header occupies row 1
                    # A failed row's importer may roll back the shared session, which expires
                    # every ORM object it holds — `job` must be re-fetched fresh both before and
                    # after each row, since even reading an expired attribute synchronously (not
                    # via `await`) raises MissingGreenlet.
                    job = await db.get(ImportJob, job_uuid)
                    assert job is not None
                    if job.status == ImportJobStatus.CANCELLED:
                        job.logs = [*job.logs, f"Cancelled after {i - 2} row(s) processed"]
                        await db.commit()
                        return

                    outcome, reason = await _process_row(db, job, requesting_user_id, i, raw_row)

                    job = await db.get(ImportJob, job_uuid)
                    assert job is not None
                    if outcome == "created":
                        created += 1
                    elif outcome == "skipped":
                        skipped += 1
                        if len(row_errors) < MAX_STORED_ROW_ERRORS:
                            row_errors.append({"row": i, "errors": [f"Skipped: {reason}"]})
                    else:
                        errored += 1
                        if len(row_errors) < MAX_STORED_ROW_ERRORS:
                            row_errors.append({"row": i, "errors": [reason]})

                    processed = i - 1
                    job.processed_rows = processed
                    job.created_count = created
                    job.skipped_count = skipped
                    job.error_count = errored
                    job.row_errors = row_errors
                    if processed % 10 == 0 or processed == len(rows):
                        job.progress_percentage = int(processed / len(rows) * 100) if rows else 100
                        await db.commit()

                job = await db.get(ImportJob, job_uuid)
                assert job is not None
                job.status = ImportJobStatus.COMPLETED
                job.progress_percentage = 100
                job.current_step = "Done"
                job.completed_at = datetime.now(UTC)
                job.logs = [
                    *job.logs,
                    f"Completed: {created} created, {skipped} skipped, {errored} errored",
                ]
                await db.commit()
            except Exception as exc:  # noqa: BLE001 - safety net so a job never sticks at RUNNING
                logger.exception("import_task_crashed", extra={"job_id": job_id})
                await db.rollback()
                job = await db.get(ImportJob, job_uuid)
                assert job is not None
                await _fail_job(db, job, f"Unexpected error: {exc}")
                raise
    finally:
        await engine.dispose()


@celery_app.task(name="import.run_import", bind=True)
def run_import(self, job_id: str) -> str:
    asyncio.run(_run_import_async(job_id))
    return "completed"
