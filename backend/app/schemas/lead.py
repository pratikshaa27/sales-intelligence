import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.lead import ActivityType, LeadPriority, LeadStatus


class CreateLeadRequest(BaseModel):
    company_id: uuid.UUID
    product_id: uuid.UUID
    contact_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    source: str = Field(default="manual", max_length=255)
    tags: list[str] = Field(default_factory=list)


class UpdateLeadRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_id: uuid.UUID | None = None
    next_action: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = None
    priority: LeadPriority | None = None


class ChangeLeadStatusRequest(BaseModel):
    status: LeadStatus
    reason: str = Field(default="", max_length=500)


class AssignLeadRequest(BaseModel):
    assigned_to: uuid.UUID | None = None


class CreateLeadNoteRequest(BaseModel):
    body: str = Field(min_length=1)


class LeadScoreOut(BaseModel):
    id: uuid.UUID
    total_score: int
    fit_score: int
    need_score: int
    authority_score: int
    timing_score: int
    confidence_score: int
    reasons: list[str]
    missing_information: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class SalesBriefOut(BaseModel):
    id: uuid.UUID
    company_overview: str
    why_relevant: str
    matched_product_summary: str
    possible_business_problem: str
    evidence_summary: list[dict]
    relevant_decision_maker: str
    suggested_opener: str
    discovery_questions: list[str]
    recommended_next_action: str
    missing_information: list[str]
    disclaimer: str
    ai_provider: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadNoteOut(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID | None
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadActivityOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    activity_type: ActivityType
    description: str
    event_metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    company_id: uuid.UUID
    contact_id: uuid.UUID | None
    product_id: uuid.UUID
    name: str
    source: str
    status: LeadStatus
    priority: LeadPriority
    total_score: int
    fit_score: int
    need_score: int
    authority_score: int
    timing_score: int
    data_confidence_score: int
    assigned_to: uuid.UUID | None
    research_summary: str
    next_action: str
    tags: list[str]
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadListItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    product_id: uuid.UUID
    name: str
    status: LeadStatus
    priority: LeadPriority
    total_score: int
    assigned_to: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductMatchSuggestion(BaseModel):
    product_id: uuid.UUID
    product_name: str
    projected_total_score: int
    projected_fit_score: int
    projected_need_score: int
    reasons: list[str]
