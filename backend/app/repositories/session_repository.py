import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import EmailVerificationToken, PasswordResetToken, Session


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str = "",
        ip_address: str = "",
    ) -> Session:
        session = Session(
            user_id=user_id,
            organization_id=organization_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_by_token_hash(self, refresh_token_hash: str) -> Session | None:
        result = await self.db.execute(
            select(Session).where(Session.refresh_token_hash == refresh_token_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        return await self.db.get(Session, session_id)

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[Session]:
        result = await self.db.execute(
            select(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
        )
        return list(result.scalars().all())

    async def revoke(self, session: Session) -> None:
        from datetime import UTC

        session.revoked_at = datetime.now(UTC)
        await self.db.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        from datetime import UTC

        sessions = await self.list_active_for_user(user_id)
        now = datetime.now(UTC)
        for s in sessions:
            s.revoked_at = now
        await self.db.flush()


class PasswordResetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        token = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: PasswordResetToken) -> None:
        from datetime import UTC

        token.used_at = datetime.now(UTC)
        await self.db.flush()


class EmailVerificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> EmailVerificationToken:
        token = EmailVerificationToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_by_token_hash(self, token_hash: str) -> EmailVerificationToken | None:
        result = await self.db.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: EmailVerificationToken) -> None:
        from datetime import UTC

        token.used_at = datetime.now(UTC)
        await self.db.flush()
