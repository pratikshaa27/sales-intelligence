import pytest

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


@pytest.mark.asyncio
async def test_admin_can_list_audit_logs(client, unique_email):
    token, _ = await _register(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/companies",
        json={"name": "Acme Robotics", "website": "https://acme.com"},
        headers=headers,
    )

    resp = await client.get("/api/v1/admin/audit-logs", headers=headers)
    assert resp.status_code == 200, resp.text
    actions = [item["action"] for item in resp.json()["data"]["items"]]
    assert "company.created" in actions
    assert "organization.registered" in actions


@pytest.mark.asyncio
async def test_admin_audit_logs_filter_by_action(client, unique_email):
    token, _ = await _register(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/v1/companies",
        json={"name": "Acme Robotics", "website": "https://acme.com"},
        headers=headers,
    )

    resp = await client.get(
        "/api/v1/admin/audit-logs", params={"action": "company.created"}, headers=headers
    )
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["action"] == "company.created"


@pytest.mark.asyncio
async def test_admin_endpoints_require_audit_logs_view_permission(client, db_session, unique_email):
    await _register(client, unique_email)
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

    resp = await client.get(
        "/api/v1/admin/audit-logs",
        headers={"Authorization": f"Bearer {read_only_token}"},
    )
    assert resp.status_code == 403

    resp2 = await client.get(
        "/api/v1/admin/security-events",
        headers={"Authorization": f"Bearer {read_only_token}"},
    )
    assert resp2.status_code == 403


@pytest.mark.asyncio
async def test_admin_audit_logs_are_tenant_isolated(client, unique_email):
    token_a, _ = await _register(client, unique_email, "Org A")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    await client.post(
        "/api/v1/companies",
        json={"name": "Org A Co", "website": "https://org-a-admin-test.com"},
        headers=headers_a,
    )

    token_b, _ = await _register(client, f"b-{unique_email}", "Org B")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    resp = await client.get("/api/v1/admin/audit-logs", headers=headers_b)
    actions = [item["action"] for item in resp.json()["data"]["items"]]
    assert "company.created" not in actions
