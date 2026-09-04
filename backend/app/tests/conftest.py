import asyncio
import os
import uuid
from collections.abc import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
# Force (not setdefault): the dev container's own .env sets APP_ENV=development, which would
# otherwise leave auth-endpoint rate limiting on and break tests that fire several requests
# in quick succession — see app/core/rate_limit.py.
os.environ["APP_ENV"] = "test"


def _force_test_database_url() -> None:
    """Point at a `..._test` database no matter what.

    docker-compose sets a real DATABASE_URL env var on the backend container (pointing at the
    dev database) so the app can run normally. Without this override, the test suite's own
    teardown — which TRUNCATEs tables between tests (see db_session below) — would silently
    run against and wipe the DEV database instead of an isolated test one. This has already
    happened once; do not remove this guard.
    """
    current = os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@postgres:5432/sales_intelligence"
    )
    base, _, db_name = current.rpartition("/")
    if not db_name.endswith("_test"):
        os.environ["DATABASE_URL"] = f"{base}/{db_name}_test"


_force_test_database_url()

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.rbac_data import PERMISSIONS, ROLE_PERMISSIONS  # noqa: E402
from app.core.seed_data import DEFAULT_PRODUCT_CATEGORIES  # noqa: E402
from app.main import app  # noqa: E402
from app.models.product import ProductCategory  # noqa: E402
from app.models.rbac import Permission, Role, RolePermission  # noqa: E402

settings = get_settings()


def _admin_url(database_url: str) -> tuple[str, str]:
    """Split an asyncpg SQLAlchemy URL into (maintenance-db URL, target db name)."""
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    db_name = sync_url.rsplit("/", 1)[-1]
    admin_url = sync_url.rsplit("/", 1)[0] + "/postgres"
    return admin_url, db_name


async def _prepare_database() -> None:
    """Create the test database (if missing), the schema, and the RBAC seed catalog.

    Runs once per test session in its own throwaway event loop via `asyncio.run` — kept
    entirely separate from pytest-asyncio's per-test loops (see `db_session` below) so no
    asyncpg connection ever gets reused across event loops, which asyncpg forbids.
    """
    admin_url, db_name = _admin_url(settings.database_url)
    admin_url_asyncpg = admin_url.replace("postgresql://", "")
    conn = await asyncpg.connect(f"postgresql://{admin_url_asyncpg}")
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)

        # Mirrors the 0002_seed_rbac migration so tests exercise the same roles/permissions
        # as a real deployment without shelling out to `alembic upgrade head`.
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            existing = await session.execute(sa.select(Role))
            if not existing.scalars().first():
                role_objs = {name: Role(name=name) for name in ROLE_PERMISSIONS}
                perm_objs = {code: Permission(code=code) for code in PERMISSIONS}
                session.add_all(role_objs.values())
                session.add_all(perm_objs.values())
                await session.flush()
                # A direct Core insert into the association table, not
                # `role_objs[name].permissions = [...]`: assigning an ORM collection
                # relationship needs to load its *current* value first to diff against, and
                # that implicit lazy-load isn't awaited, so it fails under async (same class
                # of bug documented on ProductService.reindex).
                links = [
                    {"role_id": role_objs[role_name].id, "permission_id": perm_objs[code].id}
                    for role_name, codes in ROLE_PERMISSIONS.items()
                    for code in codes
                ]
                await session.execute(sa.insert(RolePermission), links)
                await session.commit()

            # Mirrors the 0003_products migration's default category catalog.
            existing_categories = await session.execute(sa.select(ProductCategory))
            if not existing_categories.scalars().first():
                session.add_all(ProductCategory(name=name) for name in DEFAULT_PRODUCT_CATEGORIES)
                await session.commit()
    finally:
        await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _database_ready() -> None:
    asyncio.run(_prepare_database())


TRUNCATE_TABLES = [
    "audit_logs",
    "email_verification_tokens",
    "password_reset_tokens",
    "sessions",
    "organization_members",
    "users",
    "organizations",
]


@pytest_asyncio.fixture
async def db_session(_database_ready) -> AsyncGenerator[AsyncSession, None]:
    """A session bound to a fresh engine created within the current test's event loop.

    A new engine per test (rather than a session-scoped one) avoids sharing asyncpg
    connections across event loops, which pytest-asyncio's per-function loops make unsafe.
    Test isolation is via truncation (below) rather than a rollback-wrapped transaction,
    since our services call session.commit() themselves.
    """
    # No pool_pre_ping: a fresh per-test engine has no idle-connection staleness risk to guard
    # against, and pre-ping's synchronous-emulation ping has shown real conflicts with greenlet
    # context when a test also runs another engine's async work in a separate thread (see the
    # research-pipeline tests) — not worth carrying for a benefit that doesn't apply here.
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = session_factory()

    yield session

    await session.close()
    async with engine.begin() as conn:
        tables = ", ".join(TRUNCATE_TABLES)
        await conn.execute(sa.text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@example.com"
