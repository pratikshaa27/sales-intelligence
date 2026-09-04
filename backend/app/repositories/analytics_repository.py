import uuid
from collections.abc import Sequence

from sqlalchemy import Row, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, ResearchStatus
from app.models.lead import Lead, LeadActivity, LeadPriority, LeadStatus
from app.models.product import Product
from app.models.research import ResearchJob
from app.models.user import User


class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def count_researched_companies(self, *, organization_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Company)
            .where(
                Company.organization_id == organization_id,
                Company.research_status == ResearchStatus.RESEARCHED,
            )
        )
        return result.scalar_one()

    async def research_job_status_counts(
        self, *, organization_id: uuid.UUID, requested_by: uuid.UUID | None = None
    ) -> dict[str, int]:
        conditions = [ResearchJob.organization_id == organization_id]
        if requested_by is not None:
            conditions.append(ResearchJob.user_id == requested_by)
        result = await self.db.execute(
            select(ResearchJob.status, func.count()).where(*conditions).group_by(ResearchJob.status)
        )
        return {row[0].value: row[1] for row in result.all()}

    async def lead_status_counts(
        self, *, organization_id: uuid.UUID, assigned_to: uuid.UUID | None = None
    ) -> dict[str, int]:
        conditions = [Lead.organization_id == organization_id]
        if assigned_to is not None:
            conditions.append(Lead.assigned_to == assigned_to)
        result = await self.db.execute(
            select(Lead.status, func.count()).where(*conditions).group_by(Lead.status)
        )
        return {row[0].value: row[1] for row in result.all()}

    async def lead_priority_count(
        self,
        *,
        organization_id: uuid.UUID,
        assigned_to: uuid.UUID | None,
        priorities: list[LeadPriority],
    ) -> int:
        conditions = [Lead.organization_id == organization_id, Lead.priority.in_(priorities)]
        if assigned_to is not None:
            conditions.append(Lead.assigned_to == assigned_to)
        result = await self.db.execute(select(func.count()).select_from(Lead).where(*conditions))
        return result.scalar_one()

    async def average_lead_score(
        self, *, organization_id: uuid.UUID, assigned_to: uuid.UUID | None = None
    ) -> float:
        conditions = [Lead.organization_id == organization_id]
        if assigned_to is not None:
            conditions.append(Lead.assigned_to == assigned_to)
        result = await self.db.execute(select(func.avg(Lead.total_score)).where(*conditions))
        value = result.scalar_one()
        return float(value) if value is not None else 0.0

    async def average_score_by_priority(
        self, *, organization_id: uuid.UUID, assigned_to: uuid.UUID | None = None
    ) -> dict[str, float]:
        conditions = [Lead.organization_id == organization_id]
        if assigned_to is not None:
            conditions.append(Lead.assigned_to == assigned_to)
        result = await self.db.execute(
            select(Lead.priority, func.avg(Lead.total_score))
            .where(*conditions)
            .group_by(Lead.priority)
        )
        return {row[0].value: float(row[1]) if row[1] is not None else 0.0 for row in result.all()}

    async def leads_by_product(
        self, *, organization_id: uuid.UUID, assigned_to: uuid.UUID | None = None
    ) -> Sequence[Row]:
        conditions = [Lead.organization_id == organization_id]
        if assigned_to is not None:
            conditions.append(Lead.assigned_to == assigned_to)
        result = await self.db.execute(
            select(Product.id, Product.name, func.count(Lead.id))
            .join(Lead, Lead.product_id == Product.id)
            .where(*conditions)
            .group_by(Product.id, Product.name)
            .order_by(func.count(Lead.id).desc())
        )
        return result.all()

    async def leads_by_industry(
        self, *, organization_id: uuid.UUID, assigned_to: uuid.UUID | None = None
    ) -> Sequence[Row]:
        conditions = [Lead.organization_id == organization_id]
        if assigned_to is not None:
            conditions.append(Lead.assigned_to == assigned_to)
        result = await self.db.execute(
            select(Company.industry, func.count(Lead.id))
            .join(Lead, Lead.company_id == Company.id)
            .where(*conditions)
            .group_by(Company.industry)
            .order_by(func.count(Lead.id).desc())
        )
        return result.all()

    async def team_performance(self, *, organization_id: uuid.UUID) -> Sequence[Row]:
        won_count = func.sum(case((Lead.status == LeadStatus.WON, 1), else_=0))
        lost_count = func.sum(case((Lead.status == LeadStatus.LOST, 1), else_=0))
        result = await self.db.execute(
            select(
                User.id,
                User.full_name,
                func.count(Lead.id),
                won_count,
                lost_count,
                func.avg(Lead.total_score),
            )
            .join(Lead, Lead.assigned_to == User.id)
            .where(Lead.organization_id == organization_id)
            .group_by(User.id, User.full_name)
            .order_by(func.count(Lead.id).desc())
        )
        return result.all()

    async def product_performance(self, *, organization_id: uuid.UUID) -> Sequence[Row]:
        won_count = func.sum(case((Lead.status == LeadStatus.WON, 1), else_=0))
        result = await self.db.execute(
            select(
                Product.id,
                Product.name,
                func.count(Lead.id),
                func.avg(Lead.total_score),
                won_count,
            )
            .select_from(Product)
            .outerjoin(Lead, Lead.product_id == Product.id)
            .where(Product.organization_id == organization_id)
            .group_by(Product.id, Product.name)
            .order_by(func.count(Lead.id).desc())
        )
        return result.all()

    async def recent_activities(
        self, *, organization_id: uuid.UUID, assigned_to: uuid.UUID | None = None, limit: int = 20
    ) -> Sequence[Row]:
        conditions = [LeadActivity.organization_id == organization_id]
        if assigned_to is not None:
            conditions.append(Lead.assigned_to == assigned_to)
        result = await self.db.execute(
            select(LeadActivity, Lead.name)
            .join(Lead, Lead.id == LeadActivity.lead_id)
            .where(*conditions)
            .order_by(LeadActivity.created_at.desc())
            .limit(limit)
        )
        return result.all()
