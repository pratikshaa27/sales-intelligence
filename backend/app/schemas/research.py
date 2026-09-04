import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.company import SourceType
from app.models.research import EvidenceCategory, JobStatus, JobType


class ResearchJobOut(BaseModel):
    id: uuid.UUID
    job_type: JobType
    status: JobStatus
    input_parameters: dict
    progress_percentage: int
    current_step: str
    logs: list[str]
    result_summary: dict
    error_message: str
    retry_count: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscoverCompaniesRequest(BaseModel):
    industry: str = ""
    location: str = ""
    company_size: str = ""
    keywords: list[str] = Field(default_factory=list)
    number_of_companies: int = Field(default=5, ge=1, le=20)


class ResearchCompanyRequest(BaseModel):
    """Empty for now — a body is reserved for future options (e.g. which pages to crawl)."""


class ResearchEvidenceOut(BaseModel):
    id: uuid.UUID
    category: EvidenceCategory
    fact_text: str
    source_url: str
    source_title: str
    source_type: SourceType
    source_published_at: datetime | None
    retrieved_at: datetime
    confidence: int
    is_ai_generated: bool

    model_config = {"from_attributes": True}
