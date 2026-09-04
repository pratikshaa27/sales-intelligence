import uuid
from collections.abc import Sequence

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import LeadPriority, LeadStatus
from app.models.research import JobStatus
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    DashboardSummary,
    LeadsAnalytics,
    LeadsByIndustryItem,
    LeadsByProductItem,
    LeadsByStatusItem,
    LeadsFunnelItem,
    ProductPerformanceItem,
    ProductsAnalytics,
    RecentActivityItem,
    TeamAnalytics,
    TeamPerformanceItem,
)

LEAD_STATUS_ORDER = [s.value for s in LeadStatus]
HIGH_PRIORITIES = [LeadPriority.HIGH, LeadPriority.CRITICAL]


def _team_performance_items(rows: Sequence[Row]) -> list[TeamPerformanceItem]:
    items = []
    for user_id, full_name, assigned_count, won_count, lost_count, avg_score in rows:
        won_count = won_count or 0
        lost_count = lost_count or 0
        items.append(
            TeamPerformanceItem(
                user_id=user_id,
                full_name=full_name,
                assigned_count=assigned_count,
                won_count=won_count,
                lost_count=lost_count,
                win_rate=round(won_count / assigned_count * 100, 1) if assigned_count else 0.0,
                average_score=round(float(avg_score), 1) if avg_score is not None else 0.0,
            )
        )
    return items


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnalyticsRepository(db)

    async def get_dashboard(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, org_scope: bool
    ) -> DashboardSummary:
        assigned_to = None if org_scope else user_id

        status_counts = await self.repo.lead_status_counts(
            organization_id=organization_id, assigned_to=assigned_to
        )
        total_leads = sum(status_counts.values())
        high_priority = await self.repo.lead_priority_count(
            organization_id=organization_id, assigned_to=assigned_to, priorities=HIGH_PRIORITIES
        )
        avg_score = await self.repo.average_lead_score(
            organization_id=organization_id, assigned_to=assigned_to
        )
        by_product_rows = await self.repo.leads_by_product(
            organization_id=organization_id, assigned_to=assigned_to
        )
        by_industry_rows = await self.repo.leads_by_industry(
            organization_id=organization_id, assigned_to=assigned_to
        )
        job_counts = await self.repo.research_job_status_counts(
            organization_id=organization_id, requested_by=None if org_scope else user_id
        )
        researched_companies = await self.repo.count_researched_companies(
            organization_id=organization_id
        )

        team = []
        if org_scope:
            team_rows = await self.repo.team_performance(organization_id=organization_id)
            team = _team_performance_items(team_rows)

        activity_rows = await self.repo.recent_activities(
            organization_id=organization_id, assigned_to=assigned_to
        )
        recent = [
            RecentActivityItem(
                lead_id=activity.lead_id,
                lead_name=lead_name,
                activity_type=activity.activity_type.value,
                description=activity.description,
                created_at=activity.created_at,
            )
            for activity, lead_name in activity_rows
        ]

        return DashboardSummary(
            scope="organization" if org_scope else "me",
            total_leads=total_leads,
            new_leads=status_counts.get(LeadStatus.NEW.value, 0),
            assigned_leads=status_counts.get(LeadStatus.ASSIGNED.value, 0),
            contacted_leads=status_counts.get(LeadStatus.CONTACTED.value, 0),
            won_leads=status_counts.get(LeadStatus.WON.value, 0),
            lost_leads=status_counts.get(LeadStatus.LOST.value, 0),
            high_priority_leads=high_priority,
            average_lead_score=round(avg_score, 1),
            total_companies_researched=researched_companies,
            research_jobs_running=job_counts.get(JobStatus.QUEUED.value, 0)
            + job_counts.get(JobStatus.RUNNING.value, 0),
            research_jobs_completed=job_counts.get(JobStatus.COMPLETED.value, 0),
            leads_by_status=[
                LeadsByStatusItem(status=s, count=c) for s, c in status_counts.items()
            ],
            leads_by_product=[
                LeadsByProductItem(product_id=pid, product_name=name, count=count)
                for pid, name, count in by_product_rows
            ],
            leads_by_industry=[
                LeadsByIndustryItem(industry=industry or "Unknown", count=count)
                for industry, count in by_industry_rows
            ],
            team_performance=team,
            recent_activities=recent,
        )

    async def get_leads_analytics(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, org_scope: bool
    ) -> LeadsAnalytics:
        assigned_to = None if org_scope else user_id
        status_counts = await self.repo.lead_status_counts(
            organization_id=organization_id, assigned_to=assigned_to
        )
        funnel = [
            LeadsFunnelItem(status=s, count=status_counts.get(s, 0)) for s in LEAD_STATUS_ORDER
        ]
        won = status_counts.get(LeadStatus.WON.value, 0)
        lost = status_counts.get(LeadStatus.LOST.value, 0)
        win_rate = round(won / (won + lost) * 100, 1) if (won + lost) else 0.0
        avg_by_priority = await self.repo.average_score_by_priority(
            organization_id=organization_id, assigned_to=assigned_to
        )
        return LeadsAnalytics(
            scope="organization" if org_scope else "me",
            funnel=funnel,
            total_won=won,
            total_lost=lost,
            win_rate=win_rate,
            average_score_by_priority={k: round(v, 1) for k, v in avg_by_priority.items()},
        )

    async def get_products_analytics(self, *, organization_id: uuid.UUID) -> ProductsAnalytics:
        rows = await self.repo.product_performance(organization_id=organization_id)
        products = []
        for product_id, name, lead_count, avg_score, won_count in rows:
            lead_count = lead_count or 0
            won_count = won_count or 0
            products.append(
                ProductPerformanceItem(
                    product_id=product_id,
                    product_name=name,
                    lead_count=lead_count,
                    average_score=round(float(avg_score), 1) if avg_score is not None else 0.0,
                    won_count=won_count,
                    win_rate=round(won_count / lead_count * 100, 1) if lead_count else 0.0,
                )
            )
        return ProductsAnalytics(products=products)

    async def get_team_analytics(self, *, organization_id: uuid.UUID) -> TeamAnalytics:
        rows = await self.repo.team_performance(organization_id=organization_id)
        return TeamAnalytics(team=_team_performance_items(rows))
