import uuid

from pydantic import BaseModel, EmailStr, Field


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: str

    model_config = {"from_attributes": True}


class OrganizationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)


class MemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    status: str

    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str
    full_name: str = Field(min_length=2, max_length=255)


class UpdateMemberRequest(BaseModel):
    role: str | None = None
    status: str | None = None
