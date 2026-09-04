import uuid
from collections.abc import Sequence

from sqlalchemy import Row, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.company import Company
from app.models.contact import Contact
from app.models.lead import (
    Lead,
    LeadActivity,
    LeadNote,
    LeadPriority,
    LeadScore,
    LeadStatus,
    SalesBrief,
)
from app.models.product import Product
from app.models.user import User


class LeadRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, *, organization_id: uuid.UUID, lead_id: uuid.UUID) -> Lead | None:
        result = await self.db.execute(
            select(Lead)
            .options(joinedload(Lead.scores), joinedload(Lead.briefs))
            .where(Lead.id == lead_id, Lead.organization_id == organization_id)
        )
        return result.unique().scalar_one_or_none()

    async def create(self, **fields) -> Lead:
        lead = Lead(**fields)
        self.db.add(lead)
        await self.db.flush()
        return lead

    async def delete(self, lead: Lead) -> None:
        await self.db.delete(lead)

    async def find_active_for_company_and_product(
        self, *, organization_id: uuid.UUID, company_id: uuid.UUID, product_id: uuid.UUID
    ) -> Lead | None:
        """Import-time dedup (spec §17): a lead already open for this company/product pair is
        treated as a duplicate; leads that already closed (won/lost/disqualified/archived) don't
        block re-importing a fresh attempt at the same pairing."""
        closed = {
            LeadStatus.WON,
            LeadStatus.LOST,
            LeadStatus.DISQUALIFIED,
            LeadStatus.ARCHIVED,
        }
        result = await self.db.execute(
            select(Lead).where(
                Lead.organization_id == organization_id,
                Lead.company_id == company_id,
                Lead.product_id == product_id,
                Lead.status.not_in(closed),
            )
        )
        return result.scalars().first()

    async def list_paginated(
        self,
        *,
        organization_id: uuid.UUID,
        search: str | None,
        status: LeadStatus | None,
        priority: LeadPriority | None,
        product_id: uuid.UUID | None,
        company_id: uuid.UUID | None,
        assigned_to: uuid.UUID | None,
        min_score: int | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[Lead], int]:
        conditions = [Lead.organization_id == organization_id]
        if search:
            conditions.append(or_(Lead.name.ilike(f"%{search}%")))
        if status:
            conditions.append(Lead.status == status)
        if priority:
            conditions.append(Lead.priority == priority)
        if product_id:
            conditions.append(Lead.product_id == product_id)
        if company_id:
            conditions.append(Lead.company_id == company_id)
        if assigned_to:
            conditions.append(Lead.assigned_to == assigned_to)
        if min_score is not None:
            conditions.append(Lead.total_score >= min_score)

        total = (
            await self.db.execute(select(func.count()).select_from(Lead).where(*conditions))
        ).scalar_one()
        result = await self.db.execute(
            select(Lead)
            .where(*conditions)
            .order_by(Lead.total_score.desc(), Lead.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total

    async def list_for_export(
        self,
        *,
        organization_id: uuid.UUID,
        status: LeadStatus | None,
        priority: LeadPriority | None,
        product_id: uuid.UUID | None,
        company_id: uuid.UUID | None,
        assigned_to: uuid.UUID | None,
        min_score: int | None,
        limit: int,
    ) -> Sequence[Row]:
        conditions = [Lead.organization_id == organization_id]
        if status:
            conditions.append(Lead.status == status)
        if priority:
            conditions.append(Lead.priority == priority)
        if product_id:
            conditions.append(Lead.product_id == product_id)
        if company_id:
            conditions.append(Lead.company_id == company_id)
        if assigned_to:
            conditions.append(Lead.assigned_to == assigned_to)
        if min_score is not None:
            conditions.append(Lead.total_score >= min_score)

        result = await self.db.execute(
            select(Lead, Company.name, Product.name, User.full_name, Contact)
            .join(Company, Company.id == Lead.company_id)
            .join(Product, Product.id == Lead.product_id)
            .outerjoin(User, User.id == Lead.assigned_to)
            .outerjoin(Contact, Contact.id == Lead.contact_id)
            .where(*conditions)
            .order_by(Lead.created_at.desc())
            .limit(limit)
        )
        return result.all()

    async def list_product_names_by_contact_ids(
        self, *, organization_id: uuid.UUID, contact_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, list[str]]:
        """A contact has no direct product association — it only exists via whichever Leads
        reference it (Company + Product + Contact), and one contact can appear on leads for
        several different products. Used to show "which product(s) is this contact tied to" on
        the contacts list without an N+1 query per contact."""
        if not contact_ids:
            return {}
        result = await self.db.execute(
            select(Lead.contact_id, Product.name)
            .join(Product, Product.id == Lead.product_id)
            .where(
                Lead.organization_id == organization_id,
                Lead.contact_id.in_(contact_ids),
            )
            .distinct()
        )
        products_by_contact: dict[uuid.UUID, list[str]] = {}
        for contact_id, product_name in result.all():
            products_by_contact.setdefault(contact_id, []).append(product_name)
        return products_by_contact


class LeadScoreRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **fields) -> LeadScore:
        score = LeadScore(**fields)
        self.db.add(score)
        await self.db.flush()
        return score

    async def list_for_lead(self, lead_id: uuid.UUID) -> Sequence[LeadScore]:
        result = await self.db.execute(
            select(LeadScore)
            .where(LeadScore.lead_id == lead_id)
            .order_by(LeadScore.created_at.desc())
        )
        return result.scalars().all()


class SalesBriefRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **fields) -> SalesBrief:
        brief = SalesBrief(**fields)
        self.db.add(brief)
        await self.db.flush()
        return brief

    async def get_latest_for_lead(self, lead_id: uuid.UUID) -> SalesBrief | None:
        result = await self.db.execute(
            select(SalesBrief)
            .where(SalesBrief.lead_id == lead_id)
            .order_by(SalesBrief.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_lead(self, lead_id: uuid.UUID) -> Sequence[SalesBrief]:
        result = await self.db.execute(
            select(SalesBrief)
            .where(SalesBrief.lead_id == lead_id)
            .order_by(SalesBrief.created_at.desc())
        )
        return result.scalars().all()


class LeadNoteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **fields) -> LeadNote:
        note = LeadNote(**fields)
        self.db.add(note)
        await self.db.flush()
        return note

    async def list_for_lead(self, lead_id: uuid.UUID) -> Sequence[LeadNote]:
        result = await self.db.execute(
            select(LeadNote).where(LeadNote.lead_id == lead_id).order_by(LeadNote.created_at.desc())
        )
        return result.scalars().all()


class LeadActivityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **fields) -> LeadActivity:
        activity = LeadActivity(**fields)
        self.db.add(activity)
        await self.db.flush()
        return activity

    async def list_for_lead(self, lead_id: uuid.UUID) -> Sequence[LeadActivity]:
        result = await self.db.execute(
            select(LeadActivity)
            .where(LeadActivity.lead_id == lead_id)
            .order_by(LeadActivity.created_at.desc())
        )
        return result.scalars().all()
