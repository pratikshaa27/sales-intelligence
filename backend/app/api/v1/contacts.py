import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Principal, require_permission
from app.core.database import get_db
from app.models.contact import VerificationStatus
from app.schemas.common import PaginatedData, SuccessResponse
from app.schemas.contact import (
    AddContactSourceRequest,
    ContactListItem,
    ContactOut,
    ContactSourceOut,
    CreateContactRequest,
    UpdateContactRequest,
)
from app.services.contact_service import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=SuccessResponse[PaginatedData[ContactListItem]])
async def list_contacts(
    search: str | None = Query(None),
    company_id: uuid.UUID | None = Query(None),
    verification_status: VerificationStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(require_permission("contacts.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ContactService(db)
    items, products_by_contact, pagination = await service.list_paginated(
        organization_id=principal.organization_id,
        search=search,
        company_id=company_id,
        verification_status=verification_status,
        page=page,
        page_size=page_size,
    )
    data = PaginatedData(
        items=[
            ContactListItem(
                id=c.id,
                company_id=c.company_id,
                company_name=c.company.name,
                full_name=c.full_name,
                job_title=c.job_title,
                seniority=c.seniority,
                verification_status=c.verification_status,
                confidence_score=c.confidence_score,
                products=products_by_contact.get(c.id, []),
                created_at=c.created_at,
            )
            for c in items
        ],
        pagination=pagination,
    )
    return SuccessResponse(data=data)


@router.post("", response_model=SuccessResponse[ContactOut], status_code=201)
async def create_contact(
    body: CreateContactRequest,
    principal: Principal = Depends(require_permission("contacts.create")),
    db: AsyncSession = Depends(get_db),
):
    service = ContactService(db)
    contact = await service.create(
        organization_id=principal.organization_id, user_id=principal.user.id, body=body
    )
    return SuccessResponse(data=ContactOut.model_validate(contact), message="Contact created")


@router.get("/{contact_id}", response_model=SuccessResponse[ContactOut])
async def get_contact(
    contact_id: uuid.UUID,
    principal: Principal = Depends(require_permission("contacts.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ContactService(db)
    contact = await service.get(organization_id=principal.organization_id, contact_id=contact_id)
    return SuccessResponse(data=ContactOut.model_validate(contact))


@router.patch("/{contact_id}", response_model=SuccessResponse[ContactOut])
async def update_contact(
    contact_id: uuid.UUID,
    body: UpdateContactRequest,
    principal: Principal = Depends(require_permission("contacts.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = ContactService(db)
    contact = await service.update(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        contact_id=contact_id,
        body=body,
    )
    return SuccessResponse(data=ContactOut.model_validate(contact), message="Contact updated")


@router.post("/{contact_id}/verify", response_model=SuccessResponse[ContactOut])
async def verify_contact(
    contact_id: uuid.UUID,
    principal: Principal = Depends(require_permission("contacts.verify")),
    db: AsyncSession = Depends(get_db),
):
    service = ContactService(db)
    contact = await service.verify(
        organization_id=principal.organization_id, user_id=principal.user.id, contact_id=contact_id
    )
    return SuccessResponse(data=ContactOut.model_validate(contact), message="Contact verified")


@router.delete("/{contact_id}", response_model=SuccessResponse[dict])
async def delete_contact(
    contact_id: uuid.UUID,
    principal: Principal = Depends(require_permission("contacts.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = ContactService(db)
    await service.delete(
        organization_id=principal.organization_id, user_id=principal.user.id, contact_id=contact_id
    )
    return SuccessResponse(data={}, message="Contact deleted")


@router.get("/{contact_id}/sources", response_model=SuccessResponse[list[ContactSourceOut]])
async def list_contact_sources(
    contact_id: uuid.UUID,
    principal: Principal = Depends(require_permission("contacts.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ContactService(db)
    sources = await service.list_sources(
        organization_id=principal.organization_id, contact_id=contact_id
    )
    return SuccessResponse(data=[ContactSourceOut.model_validate(s) for s in sources])


@router.post(
    "/{contact_id}/sources", response_model=SuccessResponse[ContactSourceOut], status_code=201
)
async def add_contact_source(
    contact_id: uuid.UUID,
    body: AddContactSourceRequest,
    principal: Principal = Depends(require_permission("contacts.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = ContactService(db)
    source = await service.add_source(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        contact_id=contact_id,
        body=body,
    )
    return SuccessResponse(data=ContactSourceOut.model_validate(source), message="Source added")


@router.delete("/{contact_id}/sources/{source_id}", response_model=SuccessResponse[dict])
async def delete_contact_source(
    contact_id: uuid.UUID,
    source_id: uuid.UUID,
    principal: Principal = Depends(require_permission("contacts.edit")),
    db: AsyncSession = Depends(get_db),
):
    service = ContactService(db)
    await service.delete_source(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        contact_id=contact_id,
        source_id=source_id,
    )
    return SuccessResponse(data={}, message="Source removed")
