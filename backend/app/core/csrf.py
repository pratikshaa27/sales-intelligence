"""Double-submit CSRF protection (spec §4.1/§20) for the two auth endpoints that rely on a
cookie rather than a Bearer header: /auth/refresh and /auth/logout. Every other endpoint is
Bearer-token-authenticated (the access token lives in JS memory, never a cookie) so a
cross-site form/script can't make the browser attach it automatically — CSRF isn't a concern
there. SameSite=Lax on the refresh cookie already blocks most cross-site POSTs in modern
browsers, but the spec asks for CSRF protection explicitly whenever a cookie is used, so this
is defense in depth: the client must read a non-httpOnly cookie's value and echo it back in a
custom header, which a cross-site attacker cannot do without already being able to run script
on the trusted origin (at which point CSRF is the least of the problem).
"""

import hmac
import secrets

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.utils import get_client_ip
from app.models.security_event import SecurityEventSeverity, SecurityEventType
from app.repositories.security_event_repository import SecurityEventRepository

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


async def verify_csrf(request: Request, db: AsyncSession) -> None:
    cookie_value = request.cookies.get(CSRF_COOKIE_NAME)
    header_value = request.headers.get(CSRF_HEADER_NAME)
    if cookie_value and header_value and hmac.compare_digest(cookie_value, header_value):
        return

    await SecurityEventRepository(db).log(
        event_type=SecurityEventType.CSRF_REJECTED,
        severity=SecurityEventSeverity.MEDIUM,
        description=f"CSRF validation failed on {request.method} {request.url.path}",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )
    await db.commit()
    raise AppError("CSRF_VALIDATION_FAILED", "CSRF token missing or invalid", 403)
