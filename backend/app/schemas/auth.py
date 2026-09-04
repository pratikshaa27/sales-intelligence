import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterOrganizationRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    admin_full_name: str = Field(min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(min_length=12, max_length=128)

    @field_validator("admin_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one uppercase letter and one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one uppercase letter and one digit")
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one uppercase letter and one digit")
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_email_verified: bool
    is_superadmin: bool

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    user: UserOut
    organization_id: uuid.UUID
    organization_name: str
    role: str
    permissions: list[str]


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserOut
    organization_id: uuid.UUID
    role: str
    # Also handed back in the body (not just set as a cookie) because the frontend runs on a
    # different origin/port than the backend in this deployment — JS on the frontend's origin
    # cannot read a cookie the backend's origin set, so it must be told the value directly and
    # hold it in memory to echo back as the CSRF header on /auth/refresh and /auth/logout.
    csrf_token: str


class SessionOut(BaseModel):
    id: uuid.UUID
    user_agent: str
    ip_address: str
    created_at: str
    expires_at: str
    is_current: bool
