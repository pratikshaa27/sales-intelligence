import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Principal, get_current_principal
from app.core.database import get_db
from app.core.exceptions import AppError, NotFoundError, PermissionDeniedError
from app.models.import_job import ImportEntityType, ImportJobStatus
from app.repositories.import_repository import ImportJobRepository
from app.schemas.common import PaginatedData, PaginationMeta, SuccessResponse
from app.schemas.import_export import ImportJobOut, ImportPreviewResponse
from app.services.import_service import ImportService

router = APIRouter(prefix="/imports", tags=["imports"])

_ENTITY_PERMISSION = {
    ImportEntityType.COMPANY: "companies.create",
    ImportEntityType.CONTACT: "contacts.create",
    ImportEntityType.PRODUCT: "products.create",
    ImportEntityType.LEAD: "leads.create",
}


def _require_import_permission(principal: Principal, entity_type: ImportEntityType) -> None:
    if principal.user.is_superadmin:
        return
    code = _ENTITY_PERMISSION[entity_type]
    if code not in principal.permissions:
        raise PermissionDeniedError(f"This action requires the '{code}' permission")


@router.post("/{entity_type}/preview", response_model=SuccessResponse[ImportPreviewResponse])
async def preview_import(
    entity_type: ImportEntityType,
    file: UploadFile = File(...),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    _require_import_permission(principal, entity_type)
    content = await file.read()
    service = ImportService(db)
    preview = service.preview(
        entity_type=entity_type, content_type=file.content_type or "", content=content
    )
    return SuccessResponse(data=preview)


@router.post("/{entity_type}", response_model=SuccessResponse[ImportJobOut], status_code=202)
async def start_import(
    entity_type: ImportEntityType,
    file: UploadFile = File(...),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    _require_import_permission(principal, entity_type)
    content = await file.read()
    service = ImportService(db)
    job = await service.start_import(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        entity_type=entity_type,
        filename=file.filename or "import.csv",
        content_type=file.content_type or "",
        content=content,
    )
    return SuccessResponse(data=ImportJobOut.model_validate(job), message="Import job queued")


@router.get("", response_model=SuccessResponse[PaginatedData[ImportJobOut]])
async def list_imports(
    entity_type: ImportEntityType | None = Query(None),
    status: ImportJobStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    repo = ImportJobRepository(db)
    items, total = await repo.list_paginated(
        organization_id=principal.organization_id,
        entity_type=entity_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    data = PaginatedData(
        items=[ImportJobOut.model_validate(j) for j in items],
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total, total_pages=total_pages
        ),
    )
    return SuccessResponse(data=data)


@router.get("/{job_id}", response_model=SuccessResponse[ImportJobOut])
async def get_import(
    job_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    repo = ImportJobRepository(db)
    job = await repo.get_by_id(organization_id=principal.organization_id, job_id=job_id)
    if job is None:
        raise NotFoundError("Import job not found")
    return SuccessResponse(data=ImportJobOut.model_validate(job))


@router.post("/{job_id}/cancel", response_model=SuccessResponse[ImportJobOut])
async def cancel_import(
    job_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    repo = ImportJobRepository(db)
    job = await repo.get_by_id(organization_id=principal.organization_id, job_id=job_id)
    if job is None:
        raise NotFoundError("Import job not found")
    _require_import_permission(principal, job.entity_type)
    if job.status in (
        ImportJobStatus.COMPLETED,
        ImportJobStatus.FAILED,
        ImportJobStatus.CANCELLED,
    ):
        raise AppError("CONFLICT", f"Import job is already {job.status.value}", 409)

    job.status = ImportJobStatus.CANCELLED
    await db.commit()
    return SuccessResponse(
        data=ImportJobOut.model_validate(job), message="Import cancellation requested"
    )
