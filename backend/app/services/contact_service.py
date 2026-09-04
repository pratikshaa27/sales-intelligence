import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.contact import Contact, ContactSource, VerificationStatus
from app.repositories.audit_repository import AuditRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.contact_repository import ContactRepository, ContactSourceRepository
from app.repositories.lead_repository import LeadRepository
from app.schemas.common import PaginationMeta
from app.schemas.contact import AddContactSourceRequest, CreateContactRequest, UpdateContactRequest


class ContactService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.contacts = ContactRepository(db)
        self.sources = ContactSourceRepository(db)
        self.companies = CompanyRepository(db)
        self.leads = LeadRepository(db)
        self.audit = AuditRepository(db)

    async def _require_company(self, *, organization_id: uuid.UUID, company_id: uuid.UUID) -> None:
        company = await self.companies.get_by_id(
            organization_id=organization_id, company_id=company_id
        )
        if company is None:
            raise AppError("VALIDATION_ERROR", "Unknown company", 422)

    async def create(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, body: CreateContactRequest
    ) -> Contact:
        await self._require_company(organization_id=organization_id, company_id=body.company_id)

        contact = await self.contacts.create(
            organization_id=organization_id,
            created_by=user_id,
            updated_by=user_id,
            **body.model_dump(),
        )
        await self.audit.log(
            action="contact.created",
            resource_type="contact",
            resource_id=str(contact.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return await self._reload(organization_id, contact.id)

    async def get(self, *, organization_id: uuid.UUID, contact_id: uuid.UUID) -> Contact:
        contact = await self.contacts.get_by_id(
            organization_id=organization_id, contact_id=contact_id
        )
        if contact is None:
            raise NotFoundError("Contact not found")
        return contact

    async def update(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        contact_id: uuid.UUID,
        body: UpdateContactRequest,
    ) -> Contact:
        contact = await self.get(organization_id=organization_id, contact_id=contact_id)
        updates = body.model_dump(exclude_unset=True)

        if "company_id" in updates:
            await self._require_company(
                organization_id=organization_id, company_id=updates["company_id"]
            )

        for field, value in updates.items():
            setattr(contact, field, value)
        contact.updated_by = user_id

        await self.audit.log(
            action="contact.updated",
            resource_type="contact",
            resource_id=str(contact.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return await self._reload(organization_id, contact.id)

    async def verify(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, contact_id: uuid.UUID
    ) -> Contact:
        contact = await self.get(organization_id=organization_id, contact_id=contact_id)
        contact.verification_status = VerificationStatus.VERIFIED
        contact.updated_by = user_id
        await self.audit.log(
            action="contact.verified",
            resource_type="contact",
            resource_id=str(contact.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return await self._reload(organization_id, contact.id)

    async def delete(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, contact_id: uuid.UUID
    ) -> None:
        contact = await self.get(organization_id=organization_id, contact_id=contact_id)
        await self.audit.log(
            action="contact.deleted",
            resource_type="contact",
            resource_id=str(contact.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.contacts.delete(contact)
        await self.db.commit()

    async def list_paginated(
        self,
        *,
        organization_id: uuid.UUID,
        search: str | None,
        company_id: uuid.UUID | None,
        verification_status: VerificationStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Contact], dict[uuid.UUID, list[str]], PaginationMeta]:
        items, total = await self.contacts.list_paginated(
            organization_id=organization_id,
            search=search,
            company_id=company_id,
            verification_status=verification_status,
            page=page,
            page_size=page_size,
        )
        products_by_contact = await self.leads.list_product_names_by_contact_ids(
            organization_id=organization_id, contact_ids=[c.id for c in items]
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return (
            list(items),
            products_by_contact,
            PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
        )

    async def add_source(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        contact_id: uuid.UUID,
        body: AddContactSourceRequest,
    ) -> ContactSource:
        contact = await self.get(organization_id=organization_id, contact_id=contact_id)
        source = await self.sources.create(
            contact_id=contact.id,
            organization_id=organization_id,
            added_by=user_id,
            **body.model_dump(),
        )
        await self.audit.log(
            action="contact.source_added",
            resource_type="contact_source",
            resource_id=str(source.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return source

    async def list_sources(
        self, *, organization_id: uuid.UUID, contact_id: uuid.UUID
    ) -> list[ContactSource]:
        await self.get(organization_id=organization_id, contact_id=contact_id)
        return list(await self.sources.list_for_contact(contact_id))

    async def delete_source(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        contact_id: uuid.UUID,
        source_id: uuid.UUID,
    ) -> None:
        await self.get(organization_id=organization_id, contact_id=contact_id)
        source = await self.sources.get_by_id(source_id)
        if source is None or source.contact_id != contact_id:
            raise NotFoundError("Source not found")
        await self.audit.log(
            action="contact.source_removed",
            resource_type="contact_source",
            resource_id=str(source.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.sources.delete(source)
        await self.db.commit()

    async def _reload(self, organization_id: uuid.UUID, contact_id: uuid.UUID) -> Contact:
        contact = await self.contacts.get_by_id(
            organization_id=organization_id, contact_id=contact_id
        )
        assert contact is not None
        return contact
