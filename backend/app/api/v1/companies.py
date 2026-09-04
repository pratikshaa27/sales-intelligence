import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Principal, require_permission
from app.core.database import get_db
from app.models.company import ResearchStatus
from app.schemas.common import PaginatedData, SuccessResponse
from app.schemas.company import (
    AddCompanySourceRequest,
    CompanyListItem,
    CompanyOut,
    CompanySourceOut,
    CreateCompanyRequest,
    UpdateCompanyRequest,
)
from app.schemas.research import DiscoverCompaniesRequest, ResearchEvidenceOut, ResearchJobOut
from app.services.company_service import CompanyService
from app.services.research_service import ResearchJobService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("/discover", response_model=SuccessResponse[ResearchJobOut], status_code=202)
async def discover_companies(
    body: DiscoverCompaniesRequest,
    principal: Principal = Depends(require_permission("companies.discover")),
    db: AsyncSession = Depends(get_db),
):
    service = ResearchJobService(db)
    job = await service.start_company_discovery(
        organization_id=principal.organization_id, user_id=principal.user.id, body=body
    )
    return SuccessResponse(
        data=ResearchJobOut.model_validate(job),
        message="Discovery job queued — results are illustrative mock data until a real data "
        "provider is configured",
    )


@router.get("", response_model=SuccessResponse[PaginatedData[CompanyListItem]])
async def list_companies(
    search: str | None = Query(None),
    industry: str | None = Query(None),
    company_size: str | None = Query(None),
    min_confidence: int | None = Query(None, ge=0, le=100),
    research_status: ResearchStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(require_permission("companies.view")),
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    items, pagination = await service.list_paginated(
        organization_id=principal.organization_id,
        search=search,
        industry=industry,
        company_size=company_size,
        min_confidence=min_confidence,
        research_status=research_status,
        page=page,
        page_size=page_size,
    )
    data = PaginatedData(
        items=[CompanyListItem.model_validate(c) for c in items], pagination=pagination
    )
    return SuccessResponse(data=data)


@router.post("", response_model=SuccessResponse[CompanyOut], status_code=201)
async def create_company(
    body: CreateCompanyRequest,
    principal: Principal = Depends(require_permission("companies.create")),
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    company = await service.create(
        organization_id=principal.organization_id, user_id=principal.user.id, body=body
    )
    return SuccessResponse(data=CompanyOut.model_validate(company), message="Company created")


@router.get("/{company_id}", response_model=SuccessResponse[CompanyOut])
async def get_company(
    company_id: uuid.UUID,
    principal: Principal = Depends(require_permission("companies.view")),
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    company = await service.get(organization_id=principal.organization_id, company_id=company_id)
    return SuccessResponse(data=CompanyOut.model_validate(company))


@router.patch("/{company_id}", response_model=SuccessResponse[CompanyOut])
async def update_company(
    company_id: uuid.UUID,
    body: UpdateCompanyRequest,
    principal: Principal = Depends(require_permission("companies.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    company = await service.update(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        company_id=company_id,
        body=body,
    )
    return SuccessResponse(data=CompanyOut.model_validate(company), message="Company updated")


@router.delete("/{company_id}", response_model=SuccessResponse[dict])
async def delete_company(
    company_id: uuid.UUID,
    principal: Principal = Depends(require_permission("companies.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    await service.delete(
        organization_id=principal.organization_id, user_id=principal.user.id, company_id=company_id
    )
    return SuccessResponse(data={}, message="Company deleted")


@router.get("/{company_id}/sources", response_model=SuccessResponse[list[CompanySourceOut]])
async def list_company_sources(
    company_id: uuid.UUID,
    principal: Principal = Depends(require_permission("companies.view")),
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    sources = await service.list_sources(
        organization_id=principal.organization_id, company_id=company_id
    )
    return SuccessResponse(data=[CompanySourceOut.model_validate(s) for s in sources])


@router.post(
    "/{company_id}/sources", response_model=SuccessResponse[CompanySourceOut], status_code=201
)
async def add_company_source(
    company_id: uuid.UUID,
    body: AddCompanySourceRequest,
    principal: Principal = Depends(require_permission("companies.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    source = await service.add_source(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        company_id=company_id,
        body=body,
    )
    return SuccessResponse(data=CompanySourceOut.model_validate(source), message="Source added")


@router.delete("/{company_id}/sources/{source_id}", response_model=SuccessResponse[dict])
async def delete_company_source(
    company_id: uuid.UUID,
    source_id: uuid.UUID,
    principal: Principal = Depends(require_permission("companies.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    await service.delete_source(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        company_id=company_id,
        source_id=source_id,
    )
    return SuccessResponse(data={}, message="Source removed")


@router.post(
    "/{company_id}/research", response_model=SuccessResponse[ResearchJobOut], status_code=202
)
async def research_company(
    company_id: uuid.UUID,
    principal: Principal = Depends(require_permission("companies.research")),
    db: AsyncSession = Depends(get_db),
):
    service = ResearchJobService(db)
    job = await service.start_company_research(
        organization_id=principal.organization_id, user_id=principal.user.id, company_id=company_id
    )
    return SuccessResponse(data=ResearchJobOut.model_validate(job), message="Research job queued")


@router.get("/{company_id}/evidence", response_model=SuccessResponse[list[ResearchEvidenceOut]])
async def list_company_evidence(
    company_id: uuid.UUID,
    principal: Principal = Depends(require_permission("companies.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ResearchJobService(db)
    evidence = await service.list_evidence_for_company(
        organization_id=principal.organization_id, company_id=company_id
    )
    return SuccessResponse(data=[ResearchEvidenceOut.model_validate(e) for e in evidence])
