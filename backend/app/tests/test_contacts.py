import pytest


def _register_payload(org_name: str, email: str) -> dict:
    return {
        "organization_name": org_name,
        "admin_full_name": "Org Admin",
        "admin_email": email,
        "admin_password": "SuperSecret123",
    }


def _company_payload(website: str) -> dict:
    return {"name": "Acme Robotics", "website": website}


def _contact_payload(company_id: str) -> dict:
    return {
        "company_id": company_id,
        "full_name": "Jamie Rivera",
        "job_title": "VP of Engineering",
        "department": "Engineering",
        "seniority": "VP",
        "role_relevance": "Owns infrastructure purchase decisions",
        "profile_url": "https://www.linkedin.com/in/jamie-rivera",
        "business_email": "jamie.rivera@acme.com",
        "confidence_score": 65,
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
    resp = await client.post(
        "/api/v1/products",
        json={"name": "Acme Sales Copilot", "code": code, "short_description": "AI for sales"},
        headers=headers,
    )
    return resp.json()["data"]["id"]


@pytest.mark.asyncio
async def test_create_and_get_contact(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)

    resp = await client.post("/api/v1/contacts", json=_contact_payload(company_id), headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    assert body["verification_status"] == "unverified"

    get_resp = await client.get(f"/api/v1/contacts/{body['id']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["full_name"] == "Jamie Rivera"


@pytest.mark.asyncio
async def test_create_contact_rejects_unknown_company(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    payload = _contact_payload("00000000-0000-0000-0000-000000000000")
    resp = await client.post("/api/v1/contacts", json=payload, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_contact_rejects_other_orgs_company(client, unique_email):
    headers_a = await _auth_headers(client, unique_email, "Org A")
    company_id_a = await _create_company(client, headers_a)

    headers_b = await _auth_headers(client, f"b-{unique_email}", "Org B")
    resp = await client.post(
        "/api/v1/contacts", json=_contact_payload(company_id_a), headers=headers_b
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_verify_contact(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    create_resp = await client.post(
        "/api/v1/contacts", json=_contact_payload(company_id), headers=headers
    )
    contact_id = create_resp.json()["data"]["id"]

    verify_resp = await client.post(f"/api/v1/contacts/{contact_id}/verify", headers=headers)
    assert verify_resp.status_code == 200
    assert verify_resp.json()["data"]["verification_status"] == "verified"


@pytest.mark.asyncio
async def test_update_and_delete_contact(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    create_resp = await client.post(
        "/api/v1/contacts", json=_contact_payload(company_id), headers=headers
    )
    contact_id = create_resp.json()["data"]["id"]

    update_resp = await client.patch(
        f"/api/v1/contacts/{contact_id}", json={"job_title": "CTO"}, headers=headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["job_title"] == "CTO"

    delete_resp = await client.delete(f"/api/v1/contacts/{contact_id}", headers=headers)
    assert delete_resp.status_code == 200

    get_resp = await client.get(f"/api/v1/contacts/{contact_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_contacts_filter_by_company(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_a = await _create_company(client, headers, "https://company-a.com")
    company_b = await _create_company(client, headers, "https://company-b.com")

    await client.post("/api/v1/contacts", json=_contact_payload(company_a), headers=headers)
    await client.post("/api/v1/contacts", json=_contact_payload(company_b), headers=headers)

    resp = await client.get(f"/api/v1/contacts?company_id={company_a}", headers=headers)
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["company_id"] == company_a
    # The contacts list has no other way to tell which company a contact belongs to (a contact
    # has no direct link to a product — only to a company, and to a product via a Lead) — so
    # the list must carry the company's name, not just its id.
    assert items[0]["company_name"] == "Acme Robotics"


@pytest.mark.asyncio
async def test_list_contacts_shows_products_from_leads(client, unique_email):
    """A contact has no product field of its own — 'which product is this contact for' only
    exists via the leads that reference it, and one contact can be linked to several leads for
    different products. The list must surface all of them, not just one."""
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    contact_resp = await client.post(
        "/api/v1/contacts", json=_contact_payload(company_id), headers=headers
    )
    contact_id = contact_resp.json()["data"]["id"]

    product_a = await _create_product(client, headers, "PA-100")
    product_b = await _create_product(client, headers, "PB-100")

    # No leads yet — should show no products.
    resp = await client.get("/api/v1/contacts", headers=headers)
    assert resp.json()["data"]["items"][0]["products"] == []

    await client.post(
        "/api/v1/leads",
        json={
            "company_id": company_id,
            "product_id": product_a,
            "contact_id": contact_id,
            "name": "Lead A",
        },
        headers=headers,
    )
    await client.post(
        "/api/v1/leads",
        json={
            "company_id": company_id,
            "product_id": product_b,
            "contact_id": contact_id,
            "name": "Lead B",
        },
        headers=headers,
    )

    resp = await client.get("/api/v1/contacts", headers=headers)
    products = resp.json()["data"]["items"][0]["products"]
    assert set(products) == {"Acme Sales Copilot"}  # both leads use the same product name/fixture

    # A distinct product name should also show up distinctly.
    other_product_resp = await client.post(
        "/api/v1/products",
        json={"name": "Other Product", "code": "OTHER-1", "short_description": "x"},
        headers=headers,
    )
    other_product_id = other_product_resp.json()["data"]["id"]
    await client.post(
        "/api/v1/leads",
        json={
            "company_id": company_id,
            "product_id": other_product_id,
            "contact_id": contact_id,
            "name": "Lead C",
        },
        headers=headers,
    )
    resp = await client.get("/api/v1/contacts", headers=headers)
    products = resp.json()["data"]["items"][0]["products"]
    assert set(products) == {"Acme Sales Copilot", "Other Product"}


@pytest.mark.asyncio
async def test_contacts_are_tenant_isolated(client, unique_email):
    headers_a = await _auth_headers(client, unique_email, "Org A")
    company_id = await _create_company(client, headers_a)
    await client.post("/api/v1/contacts", json=_contact_payload(company_id), headers=headers_a)

    headers_b = await _auth_headers(client, f"b-{unique_email}", "Org B")
    list_resp = await client.get("/api/v1/contacts", headers=headers_b)
    assert list_resp.json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_contact_sources_crud(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    create_resp = await client.post(
        "/api/v1/contacts", json=_contact_payload(company_id), headers=headers
    )
    contact_id = create_resp.json()["data"]["id"]

    add_resp = await client.post(
        f"/api/v1/contacts/{contact_id}/sources",
        json={
            "url": "https://www.linkedin.com/in/jamie-rivera",
            "title": "LinkedIn profile",
            "source_type": "social_profile",
        },
        headers=headers,
    )
    assert add_resp.status_code == 201
    source_id = add_resp.json()["data"]["id"]

    list_resp = await client.get(f"/api/v1/contacts/{contact_id}/sources", headers=headers)
    assert len(list_resp.json()["data"]) == 1

    delete_resp = await client.delete(
        f"/api/v1/contacts/{contact_id}/sources/{source_id}", headers=headers
    )
    assert delete_resp.status_code == 200
