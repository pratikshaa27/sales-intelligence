import pytest


def _register_payload(org_name: str, email: str) -> dict:
    return {
        "organization_name": org_name,
        "admin_full_name": "Org Admin",
        "admin_email": email,
        "admin_password": "SuperSecret123",
    }


def _company_payload(website: str, name: str = "Acme Robotics") -> dict:
    return {
        "name": name,
        "website": website,
        "industry": "Robotics",
        "locations": ["San Francisco, CA"],
        "company_size": "51-200",
        "revenue_range": "$10M-$50M",
        "business_description": "Builds industrial robots.",
        "technology_stack": ["AWS", "Kubernetes"],
        "business_challenges": ["Scaling manufacturing"],
        "public_signals": ["Hiring 20 engineers"],
        "confidence_score": 70,
    }


async def _auth_headers(client, unique_email, org_name: str = "Acme Inc") -> dict:
    resp = await client.post(
        "/api/v1/auth/register", json=_register_payload(org_name, unique_email)
    )
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_company_normalizes_domain(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    resp = await client.post(
        "/api/v1/companies",
        json=_company_payload("https://www.Acme-Robotics.com/about"),
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    assert body["domain"] == "acme-robotics.com"
    assert body["research_status"] == "not_researched"


@pytest.mark.asyncio
async def test_duplicate_domain_rejected(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    await client.post(
        "/api/v1/companies", json=_company_payload("https://acme.com"), headers=headers
    )
    resp = await client.post(
        "/api/v1/companies", json=_company_payload("http://www.acme.com/"), headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_update_company_revalidates_domain_dedup(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    await client.post(
        "/api/v1/companies", json=_company_payload("https://taken.com"), headers=headers
    )
    create_resp = await client.post(
        "/api/v1/companies", json=_company_payload("https://mine.com"), headers=headers
    )
    company_id = create_resp.json()["data"]["id"]

    conflict_resp = await client.patch(
        f"/api/v1/companies/{company_id}", json={"website": "https://taken.com"}, headers=headers
    )
    assert conflict_resp.status_code == 409

    ok_resp = await client.patch(
        f"/api/v1/companies/{company_id}",
        json={"website": "https://mine-renamed.com", "industry": "Manufacturing"},
        headers=headers,
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["data"]["domain"] == "mine-renamed.com"
    assert ok_resp.json()["data"]["industry"] == "Manufacturing"


@pytest.mark.asyncio
async def test_delete_company(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    create_resp = await client.post(
        "/api/v1/companies", json=_company_payload("https://deleteme.com"), headers=headers
    )
    company_id = create_resp.json()["data"]["id"]

    delete_resp = await client.delete(f"/api/v1/companies/{company_id}", headers=headers)
    assert delete_resp.status_code == 200

    get_resp = await client.get(f"/api/v1/companies/{company_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_companies_search_and_filter(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    await client.post(
        "/api/v1/companies",
        json=_company_payload("https://acme-one.com", "Acme One"),
        headers=headers,
    )
    other = _company_payload("https://widgetco.com", "Widget Co")
    other["industry"] = "Manufacturing"
    other["confidence_score"] = 20
    await client.post("/api/v1/companies", json=other, headers=headers)

    search_resp = await client.get("/api/v1/companies?search=Acme", headers=headers)
    items = search_resp.json()["data"]["items"]
    assert all("Acme" in item["name"] for item in items)

    confidence_resp = await client.get("/api/v1/companies?min_confidence=50", headers=headers)
    confidence_items = confidence_resp.json()["data"]["items"]
    assert all(item["confidence_score"] >= 50 for item in confidence_items)
    assert len(confidence_items) == 1


@pytest.mark.asyncio
async def test_companies_are_tenant_isolated(client, unique_email):
    headers_a = await _auth_headers(client, unique_email, "Org A")
    await client.post(
        "/api/v1/companies", json=_company_payload("https://org-a-only.com"), headers=headers_a
    )

    headers_b = await _auth_headers(client, f"b-{unique_email}", "Org B")
    list_resp = await client.get("/api/v1/companies", headers=headers_b)
    assert list_resp.json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_company_sources_crud(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    create_resp = await client.post(
        "/api/v1/companies", json=_company_payload("https://sourcey.com"), headers=headers
    )
    company_id = create_resp.json()["data"]["id"]

    add_resp = await client.post(
        f"/api/v1/companies/{company_id}/sources",
        json={"url": "https://sourcey.com/about", "title": "About page", "source_type": "website"},
        headers=headers,
    )
    assert add_resp.status_code == 201
    source_id = add_resp.json()["data"]["id"]

    list_resp = await client.get(f"/api/v1/companies/{company_id}/sources", headers=headers)
    assert len(list_resp.json()["data"]) == 1

    delete_resp = await client.delete(
        f"/api/v1/companies/{company_id}/sources/{source_id}", headers=headers
    )
    assert delete_resp.status_code == 200

    empty_resp = await client.get(f"/api/v1/companies/{company_id}/sources", headers=headers)
    assert empty_resp.json()["data"] == []


@pytest.mark.asyncio
async def test_invalid_website_rejected(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    resp = await client.post("/api/v1/companies", json=_company_payload("   "), headers=headers)
    assert resp.status_code == 422
