import pytest


def _register_payload(org_name: str, email: str) -> dict:
    return {
        "organization_name": org_name,
        "admin_full_name": "Org Admin",
        "admin_email": email,
        "admin_password": "SuperSecret123",
    }


def _company_payload(website: str) -> dict:
    return {
        "name": "Acme Robotics",
        "website": website,
        "industry": "Robotics",
        "locations": ["San Francisco, CA"],
        "company_size": "51-200",
        "technology_stack": ["AWS"],
        "business_challenges": ["Scaling manufacturing operations"],
        "confidence_score": 70,
    }


def _product_payload(code: str) -> dict:
    return {
        "name": "Acme Sales Copilot",
        "code": code,
        "short_description": "AI assistant for sales teams",
        "detailed_description": "A detailed pitch for the product.",
        "target_industries": ["Robotics"],
        "target_company_size": ["51-200"],
        "target_geographic_regions": ["San Francisco, CA"],
        "business_problems": ["Manufacturing operations scaling is slow"],
        "supported_integrations": ["AWS"],
    }


async def _auth_headers(client, unique_email, org_name: str = "Acme Inc") -> dict:
    resp = await client.post(
        "/api/v1/auth/register", json=_register_payload(org_name, unique_email)
    )
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_company(client, headers, website: str = "https://acme.com") -> str:
    resp = await client.post("/api/v1/companies", json=_company_payload(website), headers=headers)
    return resp.json()["data"]["id"]


async def _create_product(client, headers, code: str = "SC-100") -> str:
    resp = await client.post("/api/v1/products", json=_product_payload(code), headers=headers)
    return resp.json()["data"]["id"]


async def _create_lead(client, headers, company_id: str, product_id: str, name: str) -> dict:
    payload = {
        "company_id": company_id,
        "product_id": product_id,
        "name": name,
        "source": "manual",
    }
    resp = await client.post("/api/v1/leads", json=payload, headers=headers)
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_dashboard_returns_organization_scope_for_admin(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead_a = await _create_lead(client, headers, company_id, product_id, "Lead A")
    lead_b = await _create_lead(client, headers, company_id, product_id, "Lead B")

    await client.post(
        f"/api/v1/leads/{lead_a['id']}/status", json={"status": "won"}, headers=headers
    )
    await client.post(
        f"/api/v1/leads/{lead_b['id']}/status", json={"status": "lost"}, headers=headers
    )

    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["scope"] == "organization"
    assert data["total_leads"] == 2
    assert data["won_leads"] == 1
    assert data["lost_leads"] == 1
    assert any(item["count"] == 2 for item in data["leads_by_product"])
    assert any(item["count"] == 2 for item in data["leads_by_industry"])
    assert isinstance(data["recent_activities"], list)
    assert len(data["recent_activities"]) > 0


@pytest.mark.asyncio
async def test_dashboard_scope_is_organization_for_admin_role(client, unique_email):
    # ORG_ADMIN holds analytics.view_org, so the dashboard reports the full-organization
    # shape (team_performance populated) rather than the "me"-scoped rep view.
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead = await _create_lead(client, headers, company_id, product_id, "Assigned lead")

    members_resp = await client.get("/api/v1/organizations/me/members", headers=headers)
    user_id = members_resp.json()["data"][0]["user_id"]
    await client.post(
        f"/api/v1/leads/{lead['id']}/assign", json={"assigned_to": user_id}, headers=headers
    )

    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    data = resp.json()["data"]
    assert data["scope"] == "organization"
    assert data["total_leads"] == 1
    assert len(data["team_performance"]) == 1
    assert data["team_performance"][0]["user_id"] == user_id


@pytest.mark.asyncio
async def test_leads_analytics_funnel_and_win_rate(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead = await _create_lead(client, headers, company_id, product_id, "Funnel lead")
    await client.post(f"/api/v1/leads/{lead['id']}/status", json={"status": "won"}, headers=headers)

    resp = await client.get("/api/v1/analytics/leads", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total_won"] == 1
    assert data["total_lost"] == 0
    assert data["win_rate"] == 100.0
    statuses = [item["status"] for item in data["funnel"]]
    assert "new" in statuses and "won" in statuses


@pytest.mark.asyncio
async def test_products_analytics_reports_lead_counts_per_product(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    await _create_lead(client, headers, company_id, product_id, "Product analytics lead")

    resp = await client.get("/api/v1/analytics/products", headers=headers)
    assert resp.status_code == 200, resp.text
    products = resp.json()["data"]["products"]
    assert any(p["product_id"] == product_id and p["lead_count"] == 1 for p in products)


@pytest.mark.asyncio
async def test_team_analytics_reports_per_user_performance(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead = await _create_lead(client, headers, company_id, product_id, "Team analytics lead")

    members_resp = await client.get("/api/v1/organizations/me/members", headers=headers)
    user_id = members_resp.json()["data"][0]["user_id"]
    await client.post(
        f"/api/v1/leads/{lead['id']}/assign", json={"assigned_to": user_id}, headers=headers
    )
    await client.post(f"/api/v1/leads/{lead['id']}/status", json={"status": "won"}, headers=headers)

    resp = await client.get("/api/v1/analytics/team", headers=headers)
    assert resp.status_code == 200, resp.text
    team = resp.json()["data"]["team"]
    assert len(team) == 1
    assert team[0]["user_id"] == user_id
    assert team[0]["assigned_count"] == 1
    assert team[0]["won_count"] == 1
    assert team[0]["win_rate"] == 100.0


@pytest.mark.asyncio
async def test_analytics_are_tenant_isolated(client, unique_email):
    headers_a = await _auth_headers(client, unique_email, "Org A")
    company_id = await _create_company(client, headers_a)
    product_id = await _create_product(client, headers_a)
    await _create_lead(client, headers_a, company_id, product_id, "Org A lead")

    headers_b = await _auth_headers(client, f"b-{unique_email}", "Org B")
    resp = await client.get("/api/v1/analytics/dashboard", headers=headers_b)
    assert resp.json()["data"]["total_leads"] == 0
