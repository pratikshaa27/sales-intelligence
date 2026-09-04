import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.company import ResearchStatus, SourceType


class CompanySourceOut(BaseModel):
    id: uuid.UUID
    url: str
    title: str
    source_type: SourceType
    published_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AddCompanySourceRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    title: str = Field(default="", max_length=500)
    source_type: SourceType = SourceType.OTHER
    published_at: datetime | None = None


class CompanyBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website: str = Field(min_length=1, max_length=500)
    industry: str = Field(default="", max_length=255)
    locations: list[str] = Field(default_factory=list)
    company_size: str = Field(default="", max_length=64)
    revenue_range: str = Field(default="", max_length=64)
    business_description: str = ""
    technology_stack: list[str] = Field(default_factory=list)
    business_challenges: list[str] = Field(default_factory=list)
    public_signals: list[str] = Field(default_factory=list)
    confidence_score: int = Field(default=0, ge=0, le=100)

    @field_validator("website")
    @classmethod
    def website_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Website is required so the company can be de-duplicated by domain")
        return v


class CreateCompanyRequest(CompanyBase):
    pass


class UpdateCompanyRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    website: str | None = Field(default=None, min_length=1, max_length=500)
    industry: str | None = None
    locations: list[str] | None = None
    company_size: str | None = None
    revenue_range: str | None = None
    business_description: str | None = None
    technology_stack: list[str] | None = None
    business_challenges: list[str] | None = None
    public_signals: list[str] | None = None
    confidence_score: int | None = Field(default=None, ge=0, le=100)
    research_status: ResearchStatus | None = None


class CompanyOut(CompanyBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    domain: str
    research_status: ResearchStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompanyListItem(BaseModel):
    id: uuid.UUID
    name: str
    domain: str
    website: str
    industry: str
    company_size: str
    confidence_score: int
    research_status: ResearchStatus
    created_at: datetime

    model_config = {"from_attributes": True}
