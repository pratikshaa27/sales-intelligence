import uuid
from datetime import datetime

from pydantic import BaseModel


class LeadsByStatusItem(BaseModel):
    status: str
    count: int


class LeadsByProductItem(BaseModel):
    product_id: uuid.UUID
    product_name: str
    count: int


class LeadsByIndustryItem(BaseModel):
    industry: str
    count: int


class TeamPerformanceItem(BaseModel):
    user_id: uuid.UUID
    full_name: str
    assigned_count: int
    won_count: int
    lost_count: int
    win_rate: float
    average_score: float


class RecentActivityItem(BaseModel):
    lead_id: uuid.UUID
    lead_name: str
    activity_type: str
    description: str
    created_at: datetime


class DashboardSummary(BaseModel):
    """Backs both the spec §8 Organization Dashboard and Sales Representative Dashboard —
    `scope` tells the frontend which one it's looking at. "me" scope filters every lead-derived
    field to leads assigned to the caller; `team_performance` (a cross-user view) is only ever
    populated for "organization" scope, gated on the analytics.view_org permission."""

    scope: str
    total_leads: int
    new_leads: int
    assigned_leads: int
    contacted_leads: int
    won_leads: int
    lost_leads: int
    high_priority_leads: int
    average_lead_score: float
    total_companies_researched: int
    research_jobs_running: int
    research_jobs_completed: int
    leads_by_status: list[LeadsByStatusItem]
    leads_by_product: list[LeadsByProductItem]
    leads_by_industry: list[LeadsByIndustryItem]
    team_performance: list[TeamPerformanceItem]
    recent_activities: list[RecentActivityItem]


class LeadsFunnelItem(BaseModel):
    status: str
    count: int


class LeadsAnalytics(BaseModel):
    scope: str
    funnel: list[LeadsFunnelItem]
    total_won: int
    total_lost: int
    win_rate: float
    average_score_by_priority: dict[str, float]


class ProductPerformanceItem(BaseModel):
    product_id: uuid.UUID
    product_name: str
    lead_count: int
    average_score: float
    won_count: int
    win_rate: float


class ProductsAnalytics(BaseModel):
    products: list[ProductPerformanceItem]


class TeamAnalytics(BaseModel):
    team: list[TeamPerformanceItem]
