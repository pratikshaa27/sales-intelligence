from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Principal, require_permission
from app.core.database import get_db
from app.schemas.analytics import DashboardSummary, LeadsAnalytics, ProductsAnalytics, TeamAnalytics
from app.schemas.common import SuccessResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _has_org_scope(principal: Principal) -> bool:
    return principal.user.is_superadmin or "analytics.view_org" in principal.permissions


@router.get("/dashboard", response_model=SuccessResponse[DashboardSummary])
async def get_dashboard(
    principal: Principal = Depends(require_permission("analytics.view_team")),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    data = await service.get_dashboard(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        org_scope=_has_org_scope(principal),
    )
    return SuccessResponse(data=data)


@router.get("/leads", response_model=SuccessResponse[LeadsAnalytics])
async def get_leads_analytics(
    principal: Principal = Depends(require_permission("analytics.view_team")),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    data = await service.get_leads_analytics(
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        org_scope=_has_org_scope(principal),
    )
    return SuccessResponse(data=data)


@router.get("/products", response_model=SuccessResponse[ProductsAnalytics])
async def get_products_analytics(
    principal: Principal = Depends(require_permission("analytics.view_org")),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    data = await service.get_products_analytics(organization_id=principal.organization_id)
    return SuccessResponse(data=data)


@router.get("/team", response_model=SuccessResponse[TeamAnalytics])
async def get_team_analytics(
    principal: Principal = Depends(require_permission("analytics.view_org")),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    data = await service.get_team_analytics(organization_id=principal.organization_id)
    return SuccessResponse(data=data)
