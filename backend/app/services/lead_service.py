import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import get_brief_provider
from app.core.exceptions import AppError, NotFoundError
from app.models.contact import Contact
from app.models.lead import ActivityType, Lead, LeadPriority, LeadStatus, SalesBrief
from app.models.research import EvidenceCategory
from app.repositories.audit_repository import AuditRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.lead_repository import (
    LeadActivityRepository,
    LeadNoteRepository,
    LeadRepository,
    LeadScoreRepository,
    SalesBriefRepository,
)
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.research_repository import ResearchEvidenceRepository
from app.schemas.common import PaginationMeta
from app.schemas.lead import (
    AssignLeadRequest,
    ChangeLeadStatusRequest,
    CreateLeadNoteRequest,
    CreateLeadRequest,
    ProductMatchSuggestion,
    UpdateLeadRequest,
)
from app.services.lead_scoring import ScoreBreakdown, calculate_lead_score, score_to_priority

SALES_BRIEF_DISCLAIMER = (
    "The opener and discovery questions below were drafted by an AI assistant from the facts "
    "on this lead. Everything else in this brief comes directly from recorded company/contact "
    "data and evidence. Review before sending — verify claims and personalize to the actual "
    "conversation."
)


class LeadService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.leads = LeadRepository(db)
        self.scores = LeadScoreRepository(db)
        self.briefs = SalesBriefRepository(db)
        self.notes = LeadNoteRepository(db)
        self.activities = LeadActivityRepository(db)
        self.companies = CompanyRepository(db)
        self.contacts = ContactRepository(db)
        self.products = ProductRepository(db)
        self.evidence = ResearchEvidenceRepository(db)
        self.organizations = OrganizationRepository(db)
        self.audit = AuditRepository(db)

    async def _log_activity(
        self,
        *,
        organization_id: uuid.UUID,
        lead_id: uuid.UUID,
        user_id: uuid.UUID | None,
        activity_type: ActivityType,
        description: str,
        event_metadata: dict | None = None,
    ) -> None:
        await self.activities.create(
            lead_id=lead_id,
            organization_id=organization_id,
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            event_metadata=event_metadata or {},
        )

    async def _score_and_apply(
        self, *, organization_id: uuid.UUID, lead: Lead, user_id: uuid.UUID | None
    ) -> ScoreBreakdown:
        company = await self.companies.get_by_id(
            organization_id=organization_id, company_id=lead.company_id
        )
        product = await self.products.get_by_id(
            organization_id=organization_id, product_id=lead.product_id
        )
        if company is None or product is None:
            raise NotFoundError("Company or product for this lead no longer exists")
        contact: Contact | None = None
        if lead.contact_id:
            contact = await self.contacts.get_by_id(
                organization_id=organization_id, contact_id=lead.contact_id
            )
        evidence = list(
            await self.evidence.list_for_company(
                organization_id=organization_id, company_id=lead.company_id
            )
        )

        breakdown = calculate_lead_score(
            company=company, product=product, contact=contact, evidence=evidence
        )

        lead.total_score = breakdown.total_score
        lead.fit_score = breakdown.fit_score
        lead.need_score = breakdown.need_score
        lead.authority_score = breakdown.authority_score
        lead.timing_score = breakdown.timing_score
        lead.data_confidence_score = breakdown.confidence_score
        if lead.priority != LeadPriority.CRITICAL:
            lead.priority = LeadPriority(score_to_priority(breakdown.total_score))

        await self.scores.create(
            lead_id=lead.id,
            organization_id=organization_id,
            total_score=breakdown.total_score,
            fit_score=breakdown.fit_score,
            need_score=breakdown.need_score,
            authority_score=breakdown.authority_score,
            timing_score=breakdown.timing_score,
            confidence_score=breakdown.confidence_score,
            reasons=breakdown.reasons,
            missing_information=breakdown.missing_information,
        )
        await self._log_activity(
            organization_id=organization_id,
            lead_id=lead.id,
            user_id=user_id,
            activity_type=ActivityType.SCORE_RECALCULATED,
            description=f"Score recalculated: {breakdown.total_score}/100",
        )
        return breakdown

    async def create(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, body: CreateLeadRequest
    ) -> Lead:
        company = await self.companies.get_by_id(
            organization_id=organization_id, company_id=body.company_id
        )
        if company is None:
            raise AppError("VALIDATION_ERROR", "Company not found", 422)
        product = await self.products.get_by_id(
            organization_id=organization_id, product_id=body.product_id
        )
        if product is None:
            raise AppError("VALIDATION_ERROR", "Product not found", 422)
        if body.contact_id:
            contact = await self.contacts.get_by_id(
                organization_id=organization_id, contact_id=body.contact_id
            )
            if contact is None:
                raise AppError("VALIDATION_ERROR", "Contact not found", 422)

        lead = await self.leads.create(
            organization_id=organization_id,
            company_id=body.company_id,
            product_id=body.product_id,
            contact_id=body.contact_id,
            name=body.name,
            source=body.source,
            tags=body.tags,
            created_by=user_id,
            updated_by=user_id,
        )
        await self._score_and_apply(organization_id=organization_id, lead=lead, user_id=user_id)
        await self._log_activity(
            organization_id=organization_id,
            lead_id=lead.id,
            user_id=user_id,
            activity_type=ActivityType.CREATED,
            description=f"Lead created from source '{body.source}'",
        )
        await self.audit.log(
            action="lead.created",
            resource_type="lead",
            resource_id=str(lead.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return await self._reload(organization_id, lead.id)

    async def get(self, *, organization_id: uuid.UUID, lead_id: uuid.UUID) -> Lead:
        lead = await self.leads.get_by_id(organization_id=organization_id, lead_id=lead_id)
        if lead is None:
            raise NotFoundError("Lead not found")
        return lead

    async def update(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        lead_id: uuid.UUID,
        body: UpdateLeadRequest,
    ) -> Lead:
        lead = await self.get(organization_id=organization_id, lead_id=lead_id)
        updates = body.model_dump(exclude_unset=True)
        if "contact_id" in updates and updates["contact_id"] is not None:
            contact = await self.contacts.get_by_id(
                organization_id=organization_id, contact_id=updates["contact_id"]
            )
            if contact is None:
                raise AppError("VALIDATION_ERROR", "Contact not found", 422)

        recompute = "contact_id" in updates
        for field, value in updates.items():
            setattr(lead, field, value)
        lead.updated_by = user_id

        if recompute:
            await self._score_and_apply(organization_id=organization_id, lead=lead, user_id=user_id)

        await self.audit.log(
            action="lead.updated",
            resource_type="lead",
            resource_id=str(lead.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return await self._reload(organization_id, lead.id)

    async def delete(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, lead_id: uuid.UUID
    ) -> None:
        lead = await self.get(organization_id=organization_id, lead_id=lead_id)
        await self.audit.log(
            action="lead.deleted",
            resource_type="lead",
            resource_id=str(lead.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.leads.delete(lead)
        await self.db.commit()

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
    ) -> tuple[list[Lead], PaginationMeta]:
        items, total = await self.leads.list_paginated(
            organization_id=organization_id,
            search=search,
            status=status,
            priority=priority,
            product_id=product_id,
            company_id=company_id,
            assigned_to=assigned_to,
            min_score=min_score,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return list(items), PaginationMeta(
            page=page, page_size=page_size, total=total, total_pages=total_pages
        )

    async def recalculate_score(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, lead_id: uuid.UUID
    ) -> Lead:
        lead = await self.get(organization_id=organization_id, lead_id=lead_id)
        await self._score_and_apply(organization_id=organization_id, lead=lead, user_id=user_id)
        await self.db.commit()
        return await self._reload(organization_id, lead.id)

    async def change_status(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        lead_id: uuid.UUID,
        body: ChangeLeadStatusRequest,
    ) -> Lead:
        lead = await self.get(organization_id=organization_id, lead_id=lead_id)
        old_status = lead.status
        if old_status == body.status:
            raise AppError("VALIDATION_ERROR", f"Lead is already '{old_status}'", 422)

        lead.status = body.status
        lead.updated_by = user_id
        description = f"Status changed from '{old_status}' to '{body.status}'"
        if body.reason:
            description += f": {body.reason}"
        await self._log_activity(
            organization_id=organization_id,
            lead_id=lead.id,
            user_id=user_id,
            activity_type=ActivityType.STATUS_CHANGED,
            description=description,
            event_metadata={"from": old_status.value, "to": body.status.value},
        )
        await self.audit.log(
            action="lead.status_changed",
            resource_type="lead",
            resource_id=str(lead.id),
            organization_id=organization_id,
            user_id=user_id,
            metadata={"from": old_status.value, "to": body.status.value},
        )
        await self.db.commit()
        return await self._reload(organization_id, lead.id)

    async def assign(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        lead_id: uuid.UUID,
        body: AssignLeadRequest,
    ) -> Lead:
        lead = await self.get(organization_id=organization_id, lead_id=lead_id)
        if body.assigned_to is not None:
            membership = await self.organizations.get_membership(
                organization_id=organization_id, user_id=body.assigned_to
            )
            if membership is None:
                raise AppError(
                    "VALIDATION_ERROR", "That user is not a member of this organization", 422
                )

        lead.assigned_to = body.assigned_to
        lead.updated_by = user_id
        if body.assigned_to is not None and lead.status == LeadStatus.NEW:
            lead.status = LeadStatus.ASSIGNED

        description = (
            f"Lead assigned to user {body.assigned_to}" if body.assigned_to else "Lead unassigned"
        )
        await self._log_activity(
            organization_id=organization_id,
            lead_id=lead.id,
            user_id=user_id,
            activity_type=ActivityType.ASSIGNED,
            description=description,
            event_metadata={"assigned_to": str(body.assigned_to) if body.assigned_to else None},
        )
        await self.audit.log(
            action="lead.assigned",
            resource_type="lead",
            resource_id=str(lead.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return await self._reload(organization_id, lead.id)

    async def add_note(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        lead_id: uuid.UUID,
        body: CreateLeadNoteRequest,
    ):
        lead = await self.get(organization_id=organization_id, lead_id=lead_id)
        note = await self.notes.create(
            lead_id=lead.id, organization_id=organization_id, author_id=user_id, body=body.body
        )
        await self._log_activity(
            organization_id=organization_id,
            lead_id=lead.id,
            user_id=user_id,
            activity_type=ActivityType.NOTE_ADDED,
            description="Note added",
        )
        await self.db.commit()
        return note

    async def list_notes(self, *, organization_id: uuid.UUID, lead_id: uuid.UUID):
        await self.get(organization_id=organization_id, lead_id=lead_id)
        return list(await self.notes.list_for_lead(lead_id))

    async def list_activities(self, *, organization_id: uuid.UUID, lead_id: uuid.UUID):
        await self.get(organization_id=organization_id, lead_id=lead_id)
        return list(await self.activities.list_for_lead(lead_id))

    async def list_scores(self, *, organization_id: uuid.UUID, lead_id: uuid.UUID):
        await self.get(organization_id=organization_id, lead_id=lead_id)
        return list(await self.scores.list_for_lead(lead_id))

    async def list_briefs(self, *, organization_id: uuid.UUID, lead_id: uuid.UUID):
        await self.get(organization_id=organization_id, lead_id=lead_id)
        return list(await self.briefs.list_for_lead(lead_id))

    async def generate_brief(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, lead_id: uuid.UUID
    ) -> SalesBrief:
        lead = await self.get(organization_id=organization_id, lead_id=lead_id)
        company = await self.companies.get_by_id(
            organization_id=organization_id, company_id=lead.company_id
        )
        product = await self.products.get_by_id(
            organization_id=organization_id, product_id=lead.product_id
        )
        if company is None or product is None:
            raise NotFoundError("Company or product for this lead no longer exists")
        contact: Contact | None = None
        if lead.contact_id:
            contact = await self.contacts.get_by_id(
                organization_id=organization_id, contact_id=lead.contact_id
            )
        evidence = list(
            await self.evidence.list_for_company(
                organization_id=organization_id, company_id=lead.company_id
            )
        )
        latest_score = await self.scores.list_for_lead(lead.id)
        reasons = latest_score[0].reasons if latest_score else []
        missing = latest_score[0].missing_information if latest_score else []

        # OVERVIEW evidence is a raw, truncated homepage-text snippet (see
        # provider.py's MockCompletionProvider) meant for at-a-glance context, not something
        # coherent enough to quote verbatim in a discovery question — exclude it here so
        # generate_conversation_starters only quotes an actual extracted fact/signal.
        quotable_evidence = [e for e in evidence if e.category != EvidenceCategory.OVERVIEW]
        evidence_bullets = [e.fact_text for e in quotable_evidence[:5] if e.fact_text]
        business_problem = ", ".join(company.business_challenges[:3])
        decision_maker = ""
        if contact:
            decision_maker = f"{contact.full_name} ({contact.job_title})".strip()

        provider = get_brief_provider()
        starters = await provider.generate_conversation_starters(
            company_name=company.name,
            product_name=product.name,
            business_problem=business_problem,
            evidence_bullets=evidence_bullets,
            decision_maker=decision_maker,
        )

        brief = await self.briefs.create(
            lead_id=lead.id,
            organization_id=organization_id,
            company_overview=company.business_description,
            why_relevant="; ".join(reasons) if reasons else "See lead score breakdown for details",
            matched_product_summary=product.short_description or product.detailed_description,
            possible_business_problem=business_problem,
            evidence_summary=[
                {"category": e.category.value, "summary": e.fact_text, "source_url": e.source_url}
                for e in evidence[:10]
            ],
            relevant_decision_maker=decision_maker,
            suggested_opener=starters.suggested_opener,
            discovery_questions=starters.discovery_questions,
            recommended_next_action=lead.next_action or "Reach out and confirm interest",
            missing_information=missing,
            disclaimer=SALES_BRIEF_DISCLAIMER,
            ai_provider=provider.name,
        )
        await self._log_activity(
            organization_id=organization_id,
            lead_id=lead.id,
            user_id=user_id,
            activity_type=ActivityType.BRIEF_GENERATED,
            description="Sales brief generated",
        )
        await self.audit.log(
            action="lead.brief_generated",
            resource_type="lead",
            resource_id=str(lead.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return brief

    async def suggest_product_matches(
        self, *, organization_id: uuid.UUID, company_id: uuid.UUID
    ) -> list[ProductMatchSuggestion]:
        company = await self.companies.get_by_id(
            organization_id=organization_id, company_id=company_id
        )
        if company is None:
            raise NotFoundError("Company not found")
        products = await self.products.list_active(organization_id=organization_id)
        evidence = list(
            await self.evidence.list_for_company(
                organization_id=organization_id, company_id=company_id
            )
        )

        suggestions = []
        for product in products:
            breakdown = calculate_lead_score(
                company=company, product=product, contact=None, evidence=evidence
            )
            suggestions.append(
                ProductMatchSuggestion(
                    product_id=product.id,
                    product_name=product.name,
                    projected_total_score=breakdown.total_score,
                    projected_fit_score=breakdown.fit_score,
                    projected_need_score=breakdown.need_score,
                    reasons=breakdown.reasons,
                )
            )
        suggestions.sort(key=lambda s: s.projected_total_score, reverse=True)
        return suggestions

    async def _reload(self, organization_id: uuid.UUID, lead_id: uuid.UUID) -> Lead:
        lead = await self.leads.get_by_id(organization_id=organization_id, lead_id=lead_id)
        assert lead is not None
        return lead
