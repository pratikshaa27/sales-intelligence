from fastapi import APIRouter

from app.api.v1 import (
    admin,
    analytics,
    auth,
    companies,
    contacts,
    imports,
    jobs,
    leads,
    organizations,
    products,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(products.router)
api_router.include_router(companies.router)
api_router.include_router(contacts.router)
api_router.include_router(jobs.router)
api_router.include_router(leads.router)
api_router.include_router(analytics.router)
api_router.include_router(imports.router)
api_router.include_router(admin.router)
