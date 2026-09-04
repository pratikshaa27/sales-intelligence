import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.security import TokenType, decode_token
from app.core.utils import get_client_ip
from app.models.security_event import SecurityEventSeverity, SecurityEventType
from app.models.user import User
from app.repositories.security_event_repository import SecurityEventRepository
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user: User
    organization_id: uuid.UUID
    permissions: list[str]


async def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Principal:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Access token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid access token") from exc

    if payload.get("type") != TokenType.ACCESS.value:
        raise UnauthorizedError("Invalid token type")

    user_id = uuid.UUID(payload["sub"])
    org_id = uuid.UUID(payload["org_id"])
    permissions = payload.get("permissions", [])

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid access token")

    request.state.user_id = str(user_id)
    request.state.organization_id = str(org_id)

    return Principal(user=user, organization_id=org_id, permissions=permissions)


async def _log_permission_denied(
    *, db: AsyncSession, request: Request, principal: Principal, description: str
) -> None:
    await SecurityEventRepository(db).log(
        event_type=SecurityEventType.PERMISSION_DENIED,
        severity=SecurityEventSeverity.MEDIUM,
        description=description,
        organization_id=principal.organization_id,
        user_id=principal.user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        metadata={"path": request.url.path, "method": request.method},
    )
    await db.commit()


def require_permission(permission_code: str):
    async def _dependency(
        request: Request,
        principal: Principal = Depends(get_current_principal),
        db: AsyncSession = Depends(get_db),
    ) -> Principal:
        if principal.user.is_superadmin:
            return principal
        if permission_code not in principal.permissions:
            await _log_permission_denied(
                db=db,
                request=request,
                principal=principal,
                description=f"Denied '{permission_code}' on {request.method} {request.url.path}",
            )
            raise PermissionDeniedError(f"This action requires the '{permission_code}' permission")
        return principal

    return _dependency


async def require_superadmin(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> Principal:
    if not principal.user.is_superadmin:
        await _log_permission_denied(
            db=db,
            request=request,
            principal=principal,
            description=f"Denied super-admin access on {request.method} {request.url.path}",
        )
        raise PermissionDeniedError("This action requires platform super-admin privileges")
    return principal
