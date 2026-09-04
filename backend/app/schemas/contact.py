import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.company import SourceType
from app.models.contact import VerificationStatus


class ContactSourceOut(BaseModel):
    id: uuid.UUID
    url: str
    title: str
    source_type: SourceType
    published_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AddContactSourceRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    title: str = Field(default="", max_length=500)
    source_type: SourceType = SourceType.OTHER
    published_at: datetime | None = None


class ContactBase(BaseModel):
    company_id: uuid.UUID
    full_name: str = Field(min_length=1, max_length=255)
    job_title: str = Field(default="", max_length=255)
    department: str = Field(default="", max_length=255)
    seniority: str = Field(default="", max_length=64)
    role_relevance: str = Field(default="", max_length=500)
    profile_url: str = Field(default="", max_length=500)
    business_email: str = Field(default="", max_length=320)
    business_phone: str = Field(default="", max_length=64)
    confidence_score: int = Field(default=0, ge=0, le=100)


class CreateContactRequest(ContactBase):
    pass


class UpdateContactRequest(BaseModel):
    company_id: uuid.UUID | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    job_title: str | None = None
    department: str | None = None
    seniority: str | None = None
    role_relevance: str | None = None
    profile_url: str | None = None
    business_email: str | None = None
    business_phone: str | None = None
    confidence_score: int | None = Field(default=None, ge=0, le=100)


class ContactOut(ContactBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContactListItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    full_name: str
    job_title: str
    seniority: str
    verification_status: VerificationStatus
    confidence_score: int
    # A contact has no direct product field — this is every distinct product from the leads
    # that currently reference this contact (empty if none do yet).
    products: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}
