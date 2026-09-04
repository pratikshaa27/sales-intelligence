import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.contact import Contact, ContactSource, VerificationStatus


class ContactRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, *, organization_id: uuid.UUID, contact_id: uuid.UUID
    ) -> Contact | None:
        result = await self.db.execute(
            select(Contact).where(
                Contact.id == contact_id, Contact.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields) -> Contact:
        contact = Contact(**fields)
        self.db.add(contact)
        await self.db.flush()
        return contact

    async def find_duplicate(
        self,
        *,
        organization_id: uuid.UUID,
        company_id: uuid.UUID,
        full_name: str,
        business_email: str,
    ) -> Contact | None:
        """Import-time dedup (spec §17 "prevent duplicate records"): match by business email
        within the company when one is given, otherwise fall back to a case-insensitive name
        match within the same company."""
        if business_email:
            result = await self.db.execute(
                select(Contact).where(
                    Contact.organization_id == organization_id,
                    Contact.company_id == company_id,
                    func.lower(Contact.business_email) == business_email.lower(),
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
        result = await self.db.execute(
            select(Contact).where(
                Contact.organization_id == organization_id,
                Contact.company_id == company_id,
                func.lower(Contact.full_name) == full_name.lower(),
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, contact: Contact) -> None:
        await self.db.delete(contact)

    async def list_paginated(
        self,
        *,
        organization_id: uuid.UUID,
        search: str | None,
        company_id: uuid.UUID | None,
        verification_status: VerificationStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[Contact], int]:
        conditions = [Contact.organization_id == organization_id]
        if search:
            like = f"%{search}%"
            conditions.append(or_(Contact.full_name.ilike(like), Contact.job_title.ilike(like)))
        if company_id:
            conditions.append(Contact.company_id == company_id)
        if verification_status:
            conditions.append(Contact.verification_status == verification_status)

        count_query = select(func.count()).select_from(Contact).where(*conditions)
        total = (await self.db.execute(count_query)).scalar_one()

        result = await self.db.execute(
            select(Contact)
            .options(joinedload(Contact.company))
            .where(*conditions)
            .order_by(Contact.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().unique().all(), total


class ContactSourceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **fields) -> ContactSource:
        source = ContactSource(**fields)
        self.db.add(source)
        await self.db.flush()
        return source

    async def list_for_contact(self, contact_id: uuid.UUID) -> Sequence[ContactSource]:
        result = await self.db.execute(
            select(ContactSource)
            .where(ContactSource.contact_id == contact_id)
            .order_by(ContactSource.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_id(self, source_id: uuid.UUID) -> ContactSource | None:
        return await self.db.get(ContactSource, source_id)

    async def delete(self, source: ContactSource) -> None:
        await self.db.delete(source)
