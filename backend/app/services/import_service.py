import csv
import io
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.storage import (
    ALLOWED_IMPORT_CONTENT_TYPES,
    MAX_IMPORT_SIZE_BYTES,
    build_import_storage_key,
    get_file_storage,
    sanitize_filename,
)
from app.models.import_job import ImportEntityType, ImportJob, ImportJobStatus
from app.repositories.audit_repository import AuditRepository
from app.repositories.import_repository import ImportJobRepository
from app.schemas.import_export import ImportPreviewResponse, RowErrorOut
from app.services.import_mapping import parse_row, validate_headers

PREVIEW_SAMPLE_ERROR_LIMIT = 20


def _validate_upload(*, content_type: str, content: bytes) -> None:
    if content_type not in ALLOWED_IMPORT_CONTENT_TYPES:
        raise AppError(
            "VALIDATION_ERROR", f"File type '{content_type}' is not allowed for CSV import", 422
        )
    if not content:
        raise AppError("VALIDATION_ERROR", "File is empty", 422)
    if len(content) > MAX_IMPORT_SIZE_BYTES:
        raise AppError(
            "VALIDATION_ERROR",
            f"File exceeds the {MAX_IMPORT_SIZE_BYTES // (1024 * 1024)}MB import size limit",
            422,
        )


def _decode_csv_rows(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    try:
        text = content.decode("utf-8-sig")  # tolerate a UTF-8 BOM from Excel-saved CSVs
    except UnicodeDecodeError as exc:
        raise AppError("VALIDATION_ERROR", "File is not valid UTF-8 text", 422) from exc
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise AppError("VALIDATION_ERROR", "CSV file has no header row", 422)
    rows = list(reader)
    return list(reader.fieldnames), rows


class ImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.jobs = ImportJobRepository(db)
        self.audit = AuditRepository(db)

    def preview(
        self, *, entity_type: ImportEntityType, content_type: str, content: bytes
    ) -> ImportPreviewResponse:
        _validate_upload(content_type=content_type, content=content)
        headers, rows = _decode_csv_rows(content)
        header_validation = validate_headers(entity_type.value, headers)

        valid_count = 0
        invalid_count = 0
        sample_errors: list[RowErrorOut] = []
        if header_validation.is_valid:
            for i, row in enumerate(rows, start=2):  # header occupies row 1
                parsed = parse_row(entity_type.value, i, row)
                if parsed.is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1
                    if len(sample_errors) < PREVIEW_SAMPLE_ERROR_LIMIT:
                        sample_errors.append(RowErrorOut(row=i, errors=parsed.errors))

        return ImportPreviewResponse(
            entity_type=entity_type,
            total_rows=len(rows),
            missing_required_columns=header_validation.missing_required,
            unknown_columns=header_validation.unknown_columns,
            valid_row_count=valid_count,
            invalid_row_count=invalid_count,
            sample_errors=sample_errors,
            can_proceed=header_validation.is_valid and len(rows) > 0,
        )

    async def start_import(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        entity_type: ImportEntityType,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> ImportJob:
        from app.workers.import_tasks import run_import

        _validate_upload(content_type=content_type, content=content)
        headers, rows = _decode_csv_rows(content)
        header_validation = validate_headers(entity_type.value, headers)
        if not header_validation.is_valid:
            raise AppError(
                "VALIDATION_ERROR",
                "CSV is missing required columns: " + ", ".join(header_validation.missing_required),
                422,
            )
        if not rows:
            raise AppError("VALIDATION_ERROR", "CSV file has no data rows", 422)

        storage = get_file_storage()
        key = build_import_storage_key(organization_id=organization_id, filename=filename)
        await storage.save(key=key, content=content)

        job = await self.jobs.create(
            organization_id=organization_id,
            user_id=user_id,
            entity_type=entity_type,
            status=ImportJobStatus.QUEUED,
            file_name=sanitize_filename(filename),
            storage_key=key,
            total_rows=len(rows),
        )
        await self.audit.log(
            action="import.requested",
            resource_type="import_job",
            resource_id=str(job.id),
            organization_id=organization_id,
            user_id=user_id,
            metadata={"entity_type": entity_type.value, "file_name": job.file_name},
        )
        await self.db.commit()

        try:
            run_import.delay(str(job.id))
        except Exception as exc:
            job.status = ImportJobStatus.FAILED
            job.error_message = "Could not queue the import (broker unavailable)"
            await self.db.commit()
            raise AppError(
                "JOB_QUEUE_UNAVAILABLE", "Could not queue the import job; try again shortly", 503
            ) from exc

        return job
