import uuid

import pytest

from app.models.company import Company, ResearchStatus
from app.models.research import JobType, ResearchJob
from app.tests.test_auth import _seed_member


def _register_payload(org_name: str, email: str) -> dict:
    return {
        "organization_name": org_name,
        "admin_full_name": "Org Admin",
        "admin_email": email,
        "admin_password": "SuperSecret123",
    }


async def _register(client, unique_email, org_name: str = "Acme Inc") -> tuple[str, str]:
    resp = await client.post(
        "/api/v1/auth/register", json=_register_payload(org_name, unique_email)
    )
    data = resp.json()["data"]
    return data["access_token"], data["organization_id"]


async def _security_events(client, token) -> list[dict]:
    resp = await client.get(
        "/api/v1/admin/security-events", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["items"]


@pytest.mark.asyncio
async def test_failed_login_creates_security_event(client, unique_email):
    token, _ = await _register(client, unique_email)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "WrongPassword123"}
    )
    assert resp.status_code == 401

    events = await _security_events(client, token)
    assert any(e["event_type"] == "login_failed" for e in events)


@pytest.mark.asyncio
async def test_repeated_failed_logins_create_lockout_event(client, unique_email):
    token, _ = await _register(client, unique_email)
    for _ in range(5):
        await client.post(
            "/api/v1/auth/login", json={"email": unique_email, "password": "WrongPassword123"}
        )

    events = await _security_events(client, token)
    lockout_events = [e for e in events if e["event_type"] == "account_locked"]
    assert len(lockout_events) == 1
    assert lockout_events[0]["severity"] == "high"


@pytest.mark.asyncio
async def test_permission_denied_creates_security_event(client, db_session, unique_email):
    admin_token, _ = await _register(client, unique_email)

    read_only_email = f"readonly-{unique_email}"
    await _seed_member(
        db_session,
        org_name="Acme Inc",
        email=read_only_email,
        password="ReadOnlyPass123",
        role_name="read_only",
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": read_only_email, "password": "ReadOnlyPass123"},
    )
    read_only_token = login_resp.json()["data"]["access_token"]

    denied_resp = await client.post(
        "/api/v1/organizations/me/invitations",
        json={"email": "rep@example.com", "role": "sales_representative", "full_name": "Rep"},
        headers={"Authorization": f"Bearer {read_only_token}"},
    )
    assert denied_resp.status_code == 403

    events = await _security_events(client, admin_token)
    denied_events = [e for e in events if e["event_type"] == "permission_denied"]
    assert len(denied_events) == 1
    assert "members.invite" in denied_events[0]["description"]


@pytest.mark.asyncio
async def test_ssrf_blocked_fetch_creates_security_event(client, db_session, unique_email):
    from app.workers import research_tasks

    token, org_id = await _register(client, unique_email)

    company = Company(
        organization_id=uuid.UUID(org_id),
        name="Internal Target",
        domain="localhost",
        website="http://127.0.0.1/",
        research_status=ResearchStatus.NOT_RESEARCHED,
    )
    db_session.add(company)
    await db_session.flush()

    job = ResearchJob(
        organization_id=uuid.UUID(org_id),
        job_type=JobType.COMPANY_RESEARCH,
        input_parameters={"company_id": str(company.id)},
    )
    db_session.add(job)
    await db_session.commit()
    job_id = str(job.id)

    await research_tasks._run_company_research_async(job_id)
    db_session.expire_all()

    events = await _security_events(client, token)
    ssrf_events = [e for e in events if e["event_type"] == "ssrf_blocked"]
    assert len(ssrf_events) == 1
    assert ssrf_events[0]["severity"] == "high"


@pytest.mark.asyncio
async def test_security_events_are_tenant_isolated(client, unique_email):
    token_a, _ = await _register(client, unique_email, "Org A")
    await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "WrongPassword123"}
    )

    token_b, _ = await _register(client, f"b-{unique_email}", "Org B")
    events_b = await _security_events(client, token_b)
    assert events_b == []
