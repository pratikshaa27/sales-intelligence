import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, UnauthorizedError
from app.core.rbac_data import ORG_ADMIN
from app.core.security import (
    create_access_token,
    decode_token,
    generate_secure_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.core.utils import slugify, unique_slug_candidate
from app.models.organization import MembershipStatus, Organization
from app.models.security_event import SecurityEventSeverity, SecurityEventType
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.rbac_repository import RBACRepository
from app.repositories.security_event_repository import SecurityEventRepository
from app.repositories.session_repository import (
    EmailVerificationRepository,
    PasswordResetRepository,
    SessionRepository,
)
from app.repositories.user_repository import UserRepository
from app.services.notification_service import send_email

settings = get_settings()

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
RESET_TOKEN_EXPIRE_MINUTES = 30
VERIFY_TOKEN_EXPIRE_HOURS = 48


@dataclass
class AuthResult:
    user: User
    organization: Organization
    role_name: str
    permissions: list[str]
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = UserRepository(db)
        self.orgs = OrganizationRepository(db)
        self.rbac = RBACRepository(db)
        self.sessions = SessionRepository(db)
        self.resets = PasswordResetRepository(db)
        self.verifications = EmailVerificationRepository(db)
        self.audit = AuditRepository(db)
        self.security_events = SecurityEventRepository(db)

    async def _issue_session(
        self,
        *,
        user: User,
        organization: Organization,
        role_name: str,
        permissions: list[str],
        ip_address: str,
        user_agent: str,
    ) -> AuthResult:
        access_token = create_access_token(str(user.id), str(organization.id), permissions)
        raw_refresh = generate_secure_token()
        refresh_expires_at = datetime.now(UTC) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
        session = await self.sessions.create(
            user_id=user.id,
            organization_id=organization.id,
            refresh_token_hash=hash_opaque_token(raw_refresh),
            expires_at=refresh_expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        # SessionRepository.create only flushes, so commit here explicitly — every caller
        # (register/login/refresh) already committed its own writes earlier in the request,
        # and without this the session row is rolled back when the request's DB session closes.
        await self.db.commit()
        # The refresh "token" handed to the client is opaque (session id + random secret,
        # matched against the hash stored on the session row) rather than a signed JWT — it
        # needs to be revocable server-side, which a self-contained JWT would not allow.
        return AuthResult(
            user=user,
            organization=organization,
            role_name=role_name,
            permissions=permissions,
            access_token=access_token,
            refresh_token=f"{session.id}.{raw_refresh}",
            refresh_expires_at=refresh_expires_at,
        )

    async def register_organization(
        self,
        *,
        organization_name: str,
        admin_full_name: str,
        admin_email: str,
        admin_password: str,
        ip_address: str,
        user_agent: str,
    ) -> AuthResult:
        existing = await self.users.get_by_email(admin_email)
        if existing:
            raise AppError("EMAIL_IN_USE", "This email is already registered", 409)

        base_slug = slugify(organization_name)
        slug = base_slug
        if await self.orgs.get_by_slug(slug):
            slug = unique_slug_candidate(base_slug)

        org = await self.orgs.create(name=organization_name, slug=slug)
        user = await self.users.create(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            full_name=admin_full_name,
        )
        role = await self.rbac.get_role_by_name(ORG_ADMIN)
        if role is None:
            raise AppError("RBAC_NOT_SEEDED", "Roles are not seeded", 500)
        await self.orgs.add_member(organization_id=org.id, user_id=user.id, role_id=role.id)
        permissions = await self.rbac.get_permission_codes_for_role(role)

        raw_token = generate_secure_token()
        await self.verifications.create(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS),
        )
        await send_email(
            to=user.email,
            subject="Verify your email",
            body=f"Verification token: {raw_token}",
        )

        await self.audit.log(
            action="organization.registered",
            resource_type="organization",
            resource_id=str(org.id),
            organization_id=org.id,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.commit()

        return await self._issue_session(
            user=user,
            organization=org,
            role_name=role.name,
            permissions=permissions,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def login(
        self, *, email: str, password: str, ip_address: str, user_agent: str
    ) -> AuthResult:
        user = await self.users.get_by_email(email)
        if user is None:
            # Do the hash comparison anyway to keep timing similar whether or not the
            # account exists, and never reveal account existence in the response.
            hash_password(password)
            raise UnauthorizedError("Invalid email or password")

        now = datetime.now(UTC)
        if user.locked_until and user.locked_until.replace(tzinfo=UTC) > now:
            raise AppError(
                "ACCOUNT_LOCKED",
                "This account is temporarily locked due to repeated failed login attempts",
                423,
            )

        if not user.is_active:
            raise UnauthorizedError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            user.failed_login_attempts += 1
            just_locked = user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS
            if just_locked:
                user.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            # Best-effort org attribution so an org admin can see brute-force attempts against
            # their own members — a user with no active membership yet (e.g. an invited-but-
            # not-yet-accepted account) simply logs without one.
            org_ids = await self._active_org_ids_for_user(user.id)
            event_org_id = org_ids[0] if org_ids else None
            await self.audit.log(
                action="auth.login_failed",
                resource_type="user",
                resource_id=str(user.id),
                organization_id=event_org_id,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.security_events.log(
                event_type=SecurityEventType.LOGIN_FAILED,
                severity=SecurityEventSeverity.LOW,
                description=f"Failed login attempt for {user.email}",
                organization_id=event_org_id,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"failed_attempts": user.failed_login_attempts},
            )
            if just_locked:
                await self.security_events.log(
                    event_type=SecurityEventType.ACCOUNT_LOCKED,
                    severity=SecurityEventSeverity.HIGH,
                    organization_id=event_org_id,
                    description=f"Account locked after repeated failed logins for {user.email}",
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            await self.db.commit()
            raise UnauthorizedError("Invalid email or password")

        user.failed_login_attempts = 0
        user.locked_until = None

        membership = None
        for candidate_org_id in await self._active_org_ids_for_user(user.id):
            membership = await self.orgs.get_membership(
                organization_id=candidate_org_id, user_id=user.id
            )
            break

        if membership is None:
            raise UnauthorizedError("This user is not an active member of any organization")

        org = await self._require_org(membership.organization_id)
        permissions = await self.rbac.get_permission_codes_for_role(membership.role)

        await self.audit.log(
            action="auth.login_success",
            resource_type="user",
            resource_id=str(user.id),
            organization_id=org.id,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.commit()

        return await self._issue_session(
            user=user,
            organization=org,
            role_name=membership.role.name,
            permissions=permissions,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def _require_org(self, organization_id: uuid.UUID) -> Organization:
        org = await self.orgs.get_by_id(organization_id)
        if org is None:
            # A membership/session referencing a non-existent organization means the FK
            # invariant was violated somewhere; this should be unreachable in practice.
            raise AppError("DATA_INTEGRITY_ERROR", "Organization not found for this account", 500)
        return org

    async def _active_org_ids_for_user(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        from sqlalchemy import select

        from app.models.organization import OrganizationMember

        result = await self.db.execute(
            select(OrganizationMember.organization_id).where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == MembershipStatus.ACTIVE,
            )
        )
        return [row[0] for row in result.all()]

    async def refresh(self, *, refresh_token: str, ip_address: str, user_agent: str) -> AuthResult:
        try:
            session_id_str, raw_secret = refresh_token.split(".", 1)
            session_id = uuid.UUID(session_id_str)
        except (ValueError, AttributeError) as exc:
            raise UnauthorizedError("Invalid refresh token") from exc

        session = await self.sessions.get_by_id(session_id)
        if session is None or session.refresh_token_hash != hash_opaque_token(raw_secret):
            raise UnauthorizedError("Invalid refresh token")
        if session.revoked_at is not None:
            raise UnauthorizedError("This session has been revoked")
        if session.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            raise UnauthorizedError("Refresh token expired")

        user = await self.users.get_by_id(session.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid refresh token")

        membership = await self.orgs.get_membership(
            organization_id=session.organization_id, user_id=user.id
        )
        if membership is None or membership.status != MembershipStatus.ACTIVE:
            raise UnauthorizedError("This user is no longer an active member of this organization")

        org = await self._require_org(session.organization_id)
        permissions = await self.rbac.get_permission_codes_for_role(membership.role)

        await self.sessions.revoke(session)
        await self.db.commit()

        return await self._issue_session(
            user=user,
            organization=org,
            role_name=membership.role.name,
            permissions=permissions,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def logout(self, *, refresh_token: str, ip_address: str, user_agent: str) -> None:
        try:
            session_id_str, raw_secret = refresh_token.split(".", 1)
            session_id = uuid.UUID(session_id_str)
        except (ValueError, AttributeError):
            return
        session = await self.sessions.get_by_id(session_id)
        if session and session.refresh_token_hash == hash_opaque_token(raw_secret):
            await self.sessions.revoke(session)
            await self.audit.log(
                action="auth.logout",
                resource_type="user",
                resource_id=str(session.user_id),
                organization_id=session.organization_id,
                user_id=session.user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.db.commit()

    async def forgot_password(self, *, email: str) -> None:
        user = await self.users.get_by_email(email)
        if user is None:
            return  # never reveal whether the account exists
        raw_token = generate_secure_token()
        await self.resets.create(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
        )
        await send_email(
            to=user.email, subject="Reset your password", body=f"Reset token: {raw_token}"
        )
        await self.db.commit()

    async def reset_password(self, *, token: str, new_password: str) -> None:
        token_hash = hash_opaque_token(token)
        reset_token = await self.resets.get_by_token_hash(token_hash)
        if (
            reset_token is None
            or reset_token.used_at is not None
            or reset_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC)
        ):
            raise AppError("INVALID_TOKEN", "This reset link is invalid or has expired", 400)

        user = await self.users.get_by_id(reset_token.user_id)
        if user is None:
            raise AppError("INVALID_TOKEN", "This reset link is invalid or has expired", 400)

        user.hashed_password = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.resets.mark_used(reset_token)
        await self.sessions.revoke_all_for_user(user.id)
        await self.audit.log(
            action="auth.password_reset",
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
        )
        await self.db.commit()

    async def change_password(
        self, *, user: User, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise UnauthorizedError("Current password is incorrect")
        user.hashed_password = hash_password(new_password)
        await self.sessions.revoke_all_for_user(user.id)
        await self.audit.log(
            action="auth.password_changed",
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
        )
        await self.db.commit()

    async def verify_email(self, *, token: str) -> None:
        token_hash = hash_opaque_token(token)
        verification = await self.verifications.get_by_token_hash(token_hash)
        if (
            verification is None
            or verification.used_at is not None
            or verification.expires_at.replace(tzinfo=UTC) < datetime.now(UTC)
        ):
            raise AppError("INVALID_TOKEN", "This verification link is invalid or has expired", 400)

        user = await self.users.get_by_id(verification.user_id)
        if user is None:
            raise AppError("INVALID_TOKEN", "This verification link is invalid or has expired", 400)

        user.is_email_verified = True
        await self.verifications.mark_used(verification)
        await self.db.commit()

    @staticmethod
    def decode_access_token(token: str) -> dict:
        return decode_token(token)
