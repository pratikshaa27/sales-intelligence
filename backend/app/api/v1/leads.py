import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Principal, require_permission
from app.core.database import get_db
from app.models.lead import LeadPriority, LeadStatus
from app.repositories.audit_repository import AuditRepository
from app.schemas.common import PaginatedData, SuccessResponse
from app.schemas.import_export import ExportLeadsRequest
from app.schemas.lead import (
    AssignLeadRequest,
    ChangeLeadStatusRequest,
    CreateLeadNoteRequest,
    CreateLeadRequest,
    LeadActivityOut,
    LeadListItem,
    LeadNoteOut,
    LeadOut,
    LeadScoreOut,
    ProductMatchSuggestion,
    SalesBriefOut,
    UpdateLeadRequest,
)
from app.services.export_service import ExportService
from app.services.lead_service import LeadService

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/export")
async def export_leads(
    body: ExportLeadsRequest,
    principal: Principal = Depends(require_permission("leads.export")),
    db: AsyncSession = Depends(get_db),
):
    service = ExportService(db)
    content, content_type, filename = await service.export_leads(
        organization_id=principal.organization_id, body=body
    )
    await AuditRepository(db).log(
        action="leads.exported",
        resource_type="lead",
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        metadata={"format": body.format, "file_name": filename},
    )
    await db.commit()
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/product-matches", response_model=SuccessResponse[list[ProductMatchSuggestion]])
async def suggest_product_matches(
    company_id: uuid.UUID = Query(...),
    principal: Principal = Depends(require_permission("leads.view")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    suggestions = await service.suggest_product_matches(
        organization_id=principal.organization_id, company_id=company_id
    )
    return SuccessResponse(data=suggestions)


@router.get("", response_model=SuccessResponse[PaginatedData[LeadListItem]])
async def list_leads(
    search: str | None = Query(None),
    status: LeadStatus | None = Query(None),
    priority: LeadPriority | None = Query(None),
    product_id: uuid.UUID | None = Query(None),
    company_id: uuid.UUID | None = Query(None),
    assigned_to: uuid.UUID | None = Query(None),
    min_score: int | None = Query(None, ge=0, le=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(require_permission("leads.view")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    items, pagination = await service.list_paginated(
        organization_id=principal.organization_id,
        search=search,
        status=status,
        priority=priority,
        product_id=product_id,
        company_id=company_id,
        assigned_to=assigned_to,
        min_score=min_score,
        page=page,
        page_size=page_size,
    )
    data = PaginatedData(
        items=[LeadListItem.model_validate(lead) for lead in items], pagination=pagination
    )
    return SuccessResponse(data=data)


@router.post("", response_model=SuccessResponse[LeadOut], status_code=201)
async def create_lead(
    body: CreateLeadRequest,
    principal: Principal = Depends(require_permission("leads.create")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    lead = await service.create(
        organization_id=principal.organization_id, user_id=principal.user.id, body=body
    )
    return SuccessResponse(data=LeadOut.model_validate(lead), message="Lead created")


@router.get("/{lead_id}", response_model=SuccessResponse[LeadOut])
async def get_lead(
    lead_id: uuid.UUID,
    principal: Principal = Depends(require_permission("leads.view")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    lead = await service.get(organization_id=principal.organization_id, lead_id=lead_id)
    return SuccessResponse(data=LeadOut.model_validate(lead))


@router.patch("/{lead_id}", response_model=SuccessResponse[LeadOut])
async def update_lead(
    lead_id: uuid.UUID,
    body: UpdateLeadRequest,
    principal: Principal = Depends(require_permission("leads.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    lead = await service.update(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        lead_id=lead_id,
        body=body,
    )
    return SuccessResponse(data=LeadOut.model_validate(lead), message="Lead updated")


@router.delete("/{lead_id}", response_model=SuccessResponse[dict])
async def delete_lead(
    lead_id: uuid.UUID,
    principal: Principal = Depends(require_permission("leads.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    await service.delete(
        organization_id=principal.organization_id, user_id=principal.user.id, lead_id=lead_id
    )
    return SuccessResponse(data={}, message="Lead deleted")


@router.post("/{lead_id}/recalculate-score", response_model=SuccessResponse[LeadOut])
async def recalculate_score(
    lead_id: uuid.UUID,
    principal: Principal = Depends(require_permission("leads.score")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    lead = await service.recalculate_score(
        organization_id=principal.organization_id, user_id=principal.user.id, lead_id=lead_id
    )
    return SuccessResponse(data=LeadOut.model_validate(lead), message="Score recalculated")


@router.get("/{lead_id}/scores", response_model=SuccessResponse[list[LeadScoreOut]])
async def list_lead_scores(
    lead_id: uuid.UUID,
    principal: Principal = Depends(require_permission("leads.view")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    scores = await service.list_scores(organization_id=principal.organization_id, lead_id=lead_id)
    return SuccessResponse(data=[LeadScoreOut.model_validate(s) for s in scores])


@router.post("/{lead_id}/status", response_model=SuccessResponse[LeadOut])
async def change_lead_status(
    lead_id: uuid.UUID,
    body: ChangeLeadStatusRequest,
    principal: Principal = Depends(require_permission("leads.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    lead = await service.change_status(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        lead_id=lead_id,
        body=body,
    )
    return SuccessResponse(data=LeadOut.model_validate(lead), message="Status updated")


@router.post("/{lead_id}/assign", response_model=SuccessResponse[LeadOut])
async def assign_lead(
    lead_id: uuid.UUID,
    body: AssignLeadRequest,
    principal: Principal = Depends(require_permission("leads.assign")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    lead = await service.assign(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        lead_id=lead_id,
        body=body,
    )
    return SuccessResponse(data=LeadOut.model_validate(lead), message="Lead assignment updated")


@router.post("/{lead_id}/brief", response_model=SuccessResponse[SalesBriefOut], status_code=201)
async def generate_brief(
    lead_id: uuid.UUID,
    principal: Principal = Depends(require_permission("leads.brief")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    brief = await service.generate_brief(
        organization_id=principal.organization_id, user_id=principal.user.id, lead_id=lead_id
    )
    return SuccessResponse(
        data=SalesBriefOut.model_validate(brief), message="Sales brief generated"
    )


@router.get("/{lead_id}/briefs", response_model=SuccessResponse[list[SalesBriefOut]])
async def list_briefs(
    lead_id: uuid.UUID,
    principal: Principal = Depends(require_permission("leads.brief")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    briefs = await service.list_briefs(organization_id=principal.organization_id, lead_id=lead_id)
    return SuccessResponse(data=[SalesBriefOut.model_validate(b) for b in briefs])


@router.get("/{lead_id}/notes", response_model=SuccessResponse[list[LeadNoteOut]])
async def list_notes(
    lead_id: uuid.UUID,
    principal: Principal = Depends(require_permission("leads.view")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    notes = await service.list_notes(organization_id=principal.organization_id, lead_id=lead_id)
    return SuccessResponse(data=[LeadNoteOut.model_validate(n) for n in notes])


@router.post("/{lead_id}/notes", response_model=SuccessResponse[LeadNoteOut], status_code=201)
async def add_note(
    lead_id: uuid.UUID,
    body: CreateLeadNoteRequest,
    principal: Principal = Depends(require_permission("leads.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    note = await service.add_note(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        lead_id=lead_id,
        body=body,
    )
    return SuccessResponse(data=LeadNoteOut.model_validate(note), message="Note added")


@router.get("/{lead_id}/activities", response_model=SuccessResponse[list[LeadActivityOut]])
async def list_activities(
    lead_id: uuid.UUID,
    principal: Principal = Depends(require_permission("leads.view")),
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    activities = await service.list_activities(
        organization_id=principal.organization_id, lead_id=lead_id
    )
    return SuccessResponse(data=[LeadActivityOut.model_validate(a) for a in activities])
