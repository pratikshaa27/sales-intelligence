import pytest


def _register_payload(email: str) -> dict:
    return {
        "organization_name": "Acme Robotics",
        "admin_full_name": "Ada Admin",
        "admin_email": email,
        "admin_password": "SuperSecret123",
    }


def _csrf_headers(client) -> dict:
    """The refresh/logout endpoints are cookie-authenticated and CSRF-protected via a
    double-submit token: a real browser reads the non-httpOnly csrf_token cookie and echoes it
    back as a header, which this mirrors for tests."""
    token = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": token} if token else {}


@pytest.mark.asyncio
async def test_register_organization_creates_org_and_admin(client, unique_email):
    resp = await client.post("/api/v1/auth/register", json=_register_payload(unique_email))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["user"]["email"] == unique_email.lower()
    assert body["data"]["role"] == "org_admin"
    assert "refresh_token" in resp.cookies
    assert "csrf_token" in resp.cookies
    # Also handed back in the body, not just the cookie: the frontend runs on a different
    # origin/port than the backend, so its JS can never read a cookie the backend's origin set
    # (see backend/app/core/csrf.py) — it has to be told the value directly instead.
    assert body["data"]["csrf_token"] == resp.cookies["csrf_token"]


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client, unique_email):
    payload = _register_payload(unique_email)
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/auth/register",
        json=_register_payload(unique_email) | {"organization_name": "Other Org"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_IN_USE"


@pytest.mark.asyncio
async def test_login_success_and_me(client, unique_email):
    payload = _register_payload(unique_email)
    await client.post("/api/v1/auth/register", json=payload)

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": payload["admin_password"]}
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["data"]["access_token"]

    me_resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_resp.status_code == 200
    me_body = me_resp.json()["data"]
    assert me_body["user"]["email"] == unique_email.lower()
    assert me_body["role"] == "org_admin"
    assert "organizations.manage" in me_body["permissions"]


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client, unique_email):
    payload = _register_payload(unique_email)
    await client.post("/api/v1/auth/register", json=payload)

    resp = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "WrongPassword123"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_account_lockout_after_repeated_failures(client, unique_email):
    payload = _register_payload(unique_email)
    await client.post("/api/v1/auth/register", json=payload)

    for _ in range(5):
        resp = await client.post(
            "/api/v1/auth/login", json={"email": unique_email, "password": "WrongPassword123"}
        )
        assert resp.status_code == 401

    locked_resp = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": payload["admin_password"]}
    )
    assert locked_resp.status_code == 423
    assert locked_resp.json()["error"]["code"] == "ACCOUNT_LOCKED"


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_old_token_invalid(client, unique_email):
    payload = _register_payload(unique_email)
    await client.post("/api/v1/auth/register", json=payload)

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": payload["admin_password"]}
    )
    old_refresh_cookie = login_resp.cookies.get("refresh_token")

    refresh_resp = await client.post("/api/v1/auth/refresh", headers=_csrf_headers(client))
    assert refresh_resp.status_code == 200

    client.cookies.set("refresh_token", old_refresh_cookie)
    reuse_resp = await client.post("/api/v1/auth/refresh", headers=_csrf_headers(client))
    assert reuse_resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_session(client, unique_email):
    payload = _register_payload(unique_email)
    await client.post("/api/v1/auth/register", json=payload)
    await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": payload["admin_password"]}
    )

    logout_resp = await client.post("/api/v1/auth/logout", headers=_csrf_headers(client))
    assert logout_resp.status_code == 200

    refresh_resp = await client.post("/api/v1/auth/refresh", headers=_csrf_headers(client))
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_permission_denied_for_read_only_role(client, db_session, unique_email):
    payload = _register_payload(unique_email)
    await client.post("/api/v1/auth/register", json=payload)

    read_only_email = f"readonly-{unique_email}"
    read_only_password = "ReadOnlyPass123"
    await _seed_member(
        db_session,
        org_name=payload["organization_name"],
        email=read_only_email,
        password=read_only_password,
        role_name="read_only",
    )

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": read_only_email, "password": read_only_password}
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    denied_resp = await client.post(
        "/api/v1/organizations/me/invitations",
        json={"email": "rep@example.com", "role": "sales_representative", "full_name": "Rep"},
        headers=headers,
    )
    assert denied_resp.status_code == 403
    assert denied_resp.json()["error"]["code"] == "PERMISSION_DENIED"

    allowed_resp = await client.get("/api/v1/organizations/me", headers=headers)
    assert allowed_resp.status_code == 200


async def _seed_member(db_session, *, org_name: str, email: str, password: str, role_name: str):
    """Add a second user with a chosen role to the already-registered organization,
    bypassing the invite endpoint (which issues an unusable random password) so tests can
    log in as that role directly."""
    from app.core.security import hash_password
    from app.repositories.organization_repository import OrganizationRepository
    from app.repositories.rbac_repository import RBACRepository
    from app.repositories.user_repository import UserRepository

    orgs = OrganizationRepository(db_session)
    org = await orgs.get_by_slug(await _slug_for(db_session, org_name))
    role = await RBACRepository(db_session).get_role_by_name(role_name)
    assert org is not None, f"organization '{org_name}' was not found"
    assert role is not None, f"role '{role_name}' is not seeded"
    user = await UserRepository(db_session).create(
        email=email, hashed_password=hash_password(password), full_name="Test User"
    )
    await orgs.add_member(organization_id=org.id, user_id=user.id, role_id=role.id)
    await db_session.commit()


async def _slug_for(db_session, org_name: str) -> str:
    import sqlalchemy as sa

    from app.models.organization import Organization

    result = await db_session.execute(
        sa.select(Organization.slug)
        .where(Organization.name == org_name)
        .order_by(Organization.created_at.desc())
    )
    return result.scalars().first()
