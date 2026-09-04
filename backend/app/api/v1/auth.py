import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Principal, get_current_principal
from app.core.config import get_settings
from app.core.csrf import CSRF_COOKIE_NAME, generate_csrf_token, verify_csrf
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.rate_limit import limiter
from app.core.utils import get_client_ip
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MeResponse,
    RegisterOrganizationRequest,
    ResetPasswordRequest,
    SessionOut,
    UserOut,
    VerifyEmailRequest,
)
from app.schemas.common import SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=max_age_seconds,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _set_csrf_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    # Deliberately NOT httponly — in a same-origin deployment the frontend could read this
    # value straight from document.cookie, but this app's frontend and backend run on
    # different origins/ports, so JS on the frontend's origin can never see a cookie the
    # backend's origin set regardless of the httponly flag. The cookie still matters — it's
    # the other half of the double-submit check verify_csrf() compares against — but the
    # *value* the frontend actually echoes back comes from the response body (see
    # AccessTokenResponse.csrf_token) and is held in memory, not read from this cookie.
    # Same max_age as the refresh cookie so the two always expire together.
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        max_age=max_age_seconds,
        httponly=False,
        secure=settings.is_production,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(key=CSRF_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _to_token_response(result, csrf_token: str) -> AccessTokenResponse:
    return AccessTokenResponse(
        access_token=result.access_token,
        expires_in_minutes=settings.jwt_access_token_expire_minutes,
        user=UserOut.model_validate(result.user),
        organization_id=result.organization.id,
        role=result.role_name,
        csrf_token=csrf_token,
    )


@router.post("/register", response_model=SuccessResponse[AccessTokenResponse], status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterOrganizationRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    result = await service.register_organization(
        organization_name=body.organization_name,
        admin_full_name=body.admin_full_name,
        admin_email=body.admin_email,
        admin_password=body.admin_password,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )
    max_age = settings.jwt_refresh_token_expire_days * 24 * 3600
    csrf_token = generate_csrf_token()
    _set_refresh_cookie(response, result.refresh_token, max_age)
    _set_csrf_cookie(response, csrf_token, max_age)
    return SuccessResponse(
        data=_to_token_response(result, csrf_token), message="Organization registered successfully"
    )


@router.post("/login", response_model=SuccessResponse[AccessTokenResponse])
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    result = await service.login(
        email=body.email,
        password=body.password,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )
    max_age = settings.jwt_refresh_token_expire_days * 24 * 3600
    csrf_token = generate_csrf_token()
    _set_refresh_cookie(response, result.refresh_token, max_age)
    _set_csrf_cookie(response, csrf_token, max_age)
    return SuccessResponse(data=_to_token_response(result, csrf_token), message="Login successful")


@router.post("/refresh", response_model=SuccessResponse[AccessTokenResponse])
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise AppError("UNAUTHORIZED", "No refresh token provided", 401)
    await verify_csrf(request, db)
    service = AuthService(db)
    result = await service.refresh(
        refresh_token=raw_refresh,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )
    max_age = settings.jwt_refresh_token_expire_days * 24 * 3600
    csrf_token = generate_csrf_token()
    _set_refresh_cookie(response, result.refresh_token, max_age)
    _set_csrf_cookie(response, csrf_token, max_age)
    return SuccessResponse(data=_to_token_response(result, csrf_token), message="Token refreshed")


@router.post("/logout", response_model=SuccessResponse[dict])
@limiter.limit("20/minute")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh:
        await verify_csrf(request, db)
        await AuthService(db).logout(
            refresh_token=raw_refresh,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
    _clear_refresh_cookie(response)
    _clear_csrf_cookie(response)
    return SuccessResponse(data={}, message="Logged out successfully")


@router.post("/forgot-password", response_model=SuccessResponse[dict])
@limiter.limit("5/minute")
async def forgot_password(
    request: Request, body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    await AuthService(db).forgot_password(email=body.email)
    return SuccessResponse(
        data={}, message="If an account with that email exists, a reset link has been sent"
    )


@router.post("/reset-password", response_model=SuccessResponse[dict])
@limiter.limit("5/minute")
async def reset_password(
    request: Request, body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    await AuthService(db).reset_password(token=body.token, new_password=body.new_password)
    return SuccessResponse(data={}, message="Password reset successfully")


@router.post("/verify-email", response_model=SuccessResponse[dict])
@limiter.limit("10/minute")
async def verify_email(
    request: Request, body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)
):
    await AuthService(db).verify_email(token=body.token)
    return SuccessResponse(data={}, message="Email verified successfully")


@router.post("/change-password", response_model=SuccessResponse[dict])
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    await AuthService(db).change_password(
        user=principal.user,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return SuccessResponse(data={}, message="Password changed successfully; please log in again")


@router.get("/me", response_model=SuccessResponse[MeResponse])
async def me(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    org_repo = OrganizationRepository(db)
    membership = await org_repo.get_membership(
        organization_id=principal.organization_id, user_id=principal.user.id
    )
    org = await org_repo.get_by_id(principal.organization_id)
    if org is None:
        raise AppError("NOT_FOUND", "Organization not found", 404)
    return SuccessResponse(
        data=MeResponse(
            user=UserOut.model_validate(principal.user),
            organization_id=org.id,
            organization_name=org.name,
            role=membership.role.name if membership else "unknown",
            permissions=principal.permissions,
        )
    )


@router.get("/sessions", response_model=SuccessResponse[list[SessionOut]])
async def list_sessions(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    sessions = await SessionRepository(db).list_active_for_user(principal.user.id)
    data = [
        SessionOut(
            id=s.id,
            user_agent=s.user_agent,
            ip_address=s.ip_address,
            created_at=s.created_at.isoformat(),
            expires_at=s.expires_at.isoformat(),
            is_current=False,
        )
        for s in sessions
    ]
    return SuccessResponse(data=data)


@router.delete("/sessions/{session_id}", response_model=SuccessResponse[dict])
async def revoke_session(
    session_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    repo = SessionRepository(db)
    session = await repo.get_by_id(session_id)
    if session is None or session.user_id != principal.user.id:
        raise AppError("NOT_FOUND", "Session not found", 404)
    await repo.revoke(session)
    await db.commit()
    return SuccessResponse(data={}, message="Session revoked")
