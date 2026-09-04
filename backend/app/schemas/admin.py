import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.security_event import SecurityEventSeverity, SecurityEventType


class AuditLogOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str
    ip_address: str
    user_agent: str
    event_metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class SecurityEventOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    user_id: uuid.UUID | None
    event_type: SecurityEventType
    severity: SecurityEventSeverity
    description: str
    ip_address: str
    user_agent: str
    event_metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}
