import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.core.utils import normalize_domain
from app.models.company import Company, CompanySource, ResearchStatus
from app.repositories.audit_repository import AuditRepository
from app.repositories.company_repository import CompanyRepository, CompanySourceRepository
from app.schemas.common import PaginationMeta
from app.schemas.company import (
    AddCompanySourceRequest,
    CreateCompanyRequest,
    UpdateCompanyRequest,
)


class CompanyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.companies = CompanyRepository(db)
        self.sources = CompanySourceRepository(db)
        self.audit = AuditRepository(db)

    async def create(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, body: CreateCompanyRequest
    ) -> Company:
        domain = normalize_domain(body.website)
        if not domain:
            raise AppError(
                "VALIDATION_ERROR", "Could not determine a domain from that website", 422
            )

        existing = await self.companies.get_by_domain(
            organization_id=organization_id, domain=domain
        )
        if existing:
            raise AppError(
                "CONFLICT",
                f"A company with domain '{domain}' already exists",
                409,
                details={"existing_company_id": str(existing.id)},
            )

        company = await self.companies.create(
            organization_id=organization_id,
            domain=domain,
            created_by=user_id,
            updated_by=user_id,
            **body.model_dump(),
        )
        await self.audit.log(
            action="company.created",
            resource_type="company",
            resource_id=str(company.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return await self._reload(organization_id, company.id)

    async def get(self, *, organization_id: uuid.UUID, company_id: uuid.UUID) -> Company:
        company = await self.companies.get_by_id(
            organization_id=organization_id, company_id=company_id
        )
        if company is None:
            raise NotFoundError("Company not found")
        return company

    async def update(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        body: UpdateCompanyRequest,
    ) -> Company:
        company = await self.get(organization_id=organization_id, company_id=company_id)
        updates = body.model_dump(exclude_unset=True)

        if "website" in updates:
            new_domain = normalize_domain(updates["website"])
            if not new_domain:
                raise AppError(
                    "VALIDATION_ERROR", "Could not determine a domain from that website", 422
                )
            if new_domain != company.domain:
                existing = await self.companies.get_by_domain(
                    organization_id=organization_id, domain=new_domain
                )
                if existing and existing.id != company.id:
                    raise AppError(
                        "CONFLICT",
                        f"A company with domain '{new_domain}' already exists",
                        409,
                        details={"existing_company_id": str(existing.id)},
                    )
                company.domain = new_domain

        for field, value in updates.items():
            setattr(company, field, value)
        company.updated_by = user_id

        await self.audit.log(
            action="company.updated",
            resource_type="company",
            resource_id=str(company.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return await self._reload(organization_id, company.id)

    async def delete(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> None:
        company = await self.get(organization_id=organization_id, company_id=company_id)
        await self.audit.log(
            action="company.deleted",
            resource_type="company",
            resource_id=str(company.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.companies.delete(company)
        await self.db.commit()

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
    ) -> tuple[list[Company], PaginationMeta]:
        items, total = await self.companies.list_paginated(
            organization_id=organization_id,
            search=search,
            industry=industry,
            company_size=company_size,
            min_confidence=min_confidence,
            research_status=research_status,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return list(items), PaginationMeta(
            page=page, page_size=page_size, total=total, total_pages=total_pages
        )

    async def add_source(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        body: AddCompanySourceRequest,
    ) -> CompanySource:
        company = await self.get(organization_id=organization_id, company_id=company_id)
        source = await self.sources.create(
            company_id=company.id,
            organization_id=organization_id,
            added_by=user_id,
            **body.model_dump(),
        )
        await self.audit.log(
            action="company.source_added",
            resource_type="company_source",
            resource_id=str(source.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return source

    async def list_sources(
        self, *, organization_id: uuid.UUID, company_id: uuid.UUID
    ) -> list[CompanySource]:
        await self.get(organization_id=organization_id, company_id=company_id)
        return list(await self.sources.list_for_company(company_id))

    async def delete_source(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        source_id: uuid.UUID,
    ) -> None:
        await self.get(organization_id=organization_id, company_id=company_id)
        source = await self.sources.get_by_id(source_id)
        if source is None or source.company_id != company_id:
            raise NotFoundError("Source not found")
        await self.audit.log(
            action="company.source_removed",
            resource_type="company_source",
            resource_id=str(source.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.sources.delete(source)
        await self.db.commit()

    async def _reload(self, organization_id: uuid.UUID, company_id: uuid.UUID) -> Company:
        company = await self.companies.get_by_id(
            organization_id=organization_id, company_id=company_id
        )
        assert company is not None
        return company
