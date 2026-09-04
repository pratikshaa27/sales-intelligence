from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Principal, require_permission
from app.core.database import get_db
from app.models.security_event import SecurityEventSeverity, SecurityEventType
from app.repositories.audit_repository import AuditRepository
from app.repositories.security_event_repository import SecurityEventRepository
from app.schemas.admin import AuditLogOut, SecurityEventOut
from app.schemas.common import PaginatedData, PaginationMeta, SuccessResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-logs", response_model=SuccessResponse[PaginatedData[AuditLogOut]])
async def list_audit_logs(
    action: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(require_permission("audit_logs.view")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await AuditRepository(db).list_paginated(
        organization_id=principal.organization_id, action=action, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    data = PaginatedData(
        items=[AuditLogOut.model_validate(i) for i in items],
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total, total_pages=total_pages
        ),
    )
    return SuccessResponse(data=data)


@router.get("/security-events", response_model=SuccessResponse[PaginatedData[SecurityEventOut]])
async def list_security_events(
    event_type: SecurityEventType | None = Query(None),
    severity: SecurityEventSeverity | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(require_permission("audit_logs.view")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await SecurityEventRepository(db).list_paginated(
        organization_id=principal.organization_id,
        event_type=event_type,
        severity=severity,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    data = PaginatedData(
        items=[SecurityEventOut.model_validate(i) for i in items],
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total, total_pages=total_pages
        ),
    )
    return SuccessResponse(data=data)
