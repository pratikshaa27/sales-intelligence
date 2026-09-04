import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanySource, ResearchStatus


class CompanyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, *, organization_id: uuid.UUID, company_id: uuid.UUID
    ) -> Company | None:
        result = await self.db.execute(
            select(Company).where(
                Company.id == company_id, Company.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_domain(self, *, organization_id: uuid.UUID, domain: str) -> Company | None:
        result = await self.db.execute(
            select(Company).where(
                Company.organization_id == organization_id, Company.domain == domain
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields) -> Company:
        company = Company(**fields)
        self.db.add(company)
        await self.db.flush()
        return company

    async def delete(self, company: Company) -> None:
        await self.db.delete(company)

    async def list_paginated(
        self,
        *,
        organization_id: uuid.UUID,
        search: str | None,
        industry: str | None,
        company_size: str | None,
        min_confidence: int | None,
        research_status: ResearchStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[Company], int]:
        conditions = [Company.organization_id == organization_id]
        if search:
            like = f"%{search}%"
            conditions.append(or_(Company.name.ilike(like), Company.domain.ilike(like)))
        if industry:
            conditions.append(Company.industry.ilike(industry))
        if company_size:
            conditions.append(Company.company_size == company_size)
        if min_confidence is not None:
            conditions.append(Company.confidence_score >= min_confidence)
        if research_status:
            conditions.append(Company.research_status == research_status)

        count_query = select(func.count()).select_from(Company).where(*conditions)
        total = (await self.db.execute(count_query)).scalar_one()

        result = await self.db.execute(
            select(Company)
            .where(*conditions)
            .order_by(Company.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total


class CompanySourceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **fields) -> CompanySource:
        source = CompanySource(**fields)
        self.db.add(source)
        await self.db.flush()
        return source

    async def list_for_company(self, company_id: uuid.UUID) -> Sequence[CompanySource]:
        result = await self.db.execute(
            select(CompanySource)
            .where(CompanySource.company_id == company_id)
            .order_by(CompanySource.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_id(self, source_id: uuid.UUID) -> CompanySource | None:
        return await self.db.get(CompanySource, source_id)

    async def delete(self, source: CompanySource) -> None:
        await self.db.delete(source)
