import pytest

from app.ai.provider import MockEmbeddingProvider
from app.tests.test_auth import _seed_member
from app.workers.product_tasks import compose_embedding_text


def _register_payload(org_name: str, email: str) -> dict:
    return {
        "organization_name": org_name,
        "admin_full_name": "Org Admin",
        "admin_email": email,
        "admin_password": "SuperSecret123",
    }


def _product_payload(code: str) -> dict:
    return {
        "name": "Acme Sales Copilot",
        "code": code,
        "short_description": "AI assistant for sales teams",
        "detailed_description": "A detailed pitch for the product.",
        "target_industries": ["Software", "Financial Services"],
        "target_company_size": ["51-200", "201-1000"],
        "target_geographic_regions": ["North America"],
        "business_problems": ["Slow lead research", "Low rep productivity"],
        "key_features": ["Lead scoring", "Sales briefs"],
        "benefits": ["Saves time", "More qualified pipeline"],
        "pricing_model": "Per-seat subscription",
        "minimum_contract_value": 5000,
        "required_technical_capabilities": ["REST API access"],
        "supported_integrations": ["Salesforce", "HubSpot"],
        "ideal_customer_profile": "B2B SaaS companies with a sales team of 10+",
        "common_use_cases": ["Outbound prospecting"],
        "competitor_alternatives": ["Generic CRM plugins"],
    }


async def _auth_headers(client, unique_email) -> dict:
    resp = await client.post(
        "/api/v1/auth/register", json=_register_payload("Acme Inc", unique_email)
    )
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_and_get_product(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    resp = await client.post("/api/v1/products", json=_product_payload("SC-100"), headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    assert body["status"] == "draft"
    assert body["embedding_status"] == "none"

    get_resp = await client.get(f"/api/v1/products/{body['id']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["code"] == "SC-100"


@pytest.mark.asyncio
async def test_duplicate_product_code_rejected(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    await client.post("/api/v1/products", json=_product_payload("SC-200"), headers=headers)
    resp = await client.post("/api/v1/products", json=_product_payload("SC-200"), headers=headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_update_product_and_activate(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    create_resp = await client.post(
        "/api/v1/products", json=_product_payload("SC-300"), headers=headers
    )
    product_id = create_resp.json()["data"]["id"]

    update_resp = await client.patch(
        f"/api/v1/products/{product_id}",
        json={"status": "active", "short_description": "Updated pitch"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    body = update_resp.json()["data"]
    assert body["status"] == "active"
    assert body["short_description"] == "Updated pitch"


@pytest.mark.asyncio
async def test_cannot_set_archived_via_patch(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    create_resp = await client.post(
        "/api/v1/products", json=_product_payload("SC-400"), headers=headers
    )
    product_id = create_resp.json()["data"]["id"]

    resp = await client.patch(
        f"/api/v1/products/{product_id}", json={"status": "archived"}, headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_archive_and_restore_product(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    create_resp = await client.post(
        "/api/v1/products", json=_product_payload("SC-500"), headers=headers
    )
    product_id = create_resp.json()["data"]["id"]

    archive_resp = await client.post(f"/api/v1/products/{product_id}/archive", headers=headers)
    assert archive_resp.status_code == 200
    assert archive_resp.json()["data"]["status"] == "archived"

    restore_resp = await client.post(f"/api/v1/products/{product_id}/restore", headers=headers)
    assert restore_resp.status_code == 200
    assert restore_resp.json()["data"]["status"] == "draft"


@pytest.mark.asyncio
async def test_cannot_leave_archived_via_patch(client, unique_email):
    """PATCH must not be usable to bypass POST /restore's "always goes back to draft" rule —
    an archived product can only ever leave that state through the dedicated restore endpoint."""
    headers = await _auth_headers(client, unique_email)
    create_resp = await client.post(
        "/api/v1/products", json=_product_payload("SC-550"), headers=headers
    )
    product_id = create_resp.json()["data"]["id"]

    await client.post(f"/api/v1/products/{product_id}/archive", headers=headers)

    resp = await client.patch(
        f"/api/v1/products/{product_id}", json={"status": "active"}, headers=headers
    )
    assert resp.status_code == 422

    get_resp = await client.get(f"/api/v1/products/{product_id}", headers=headers)
    assert get_resp.json()["data"]["status"] == "archived"


@pytest.mark.asyncio
async def test_delete_only_allowed_for_draft(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    create_resp = await client.post(
        "/api/v1/products", json=_product_payload("SC-600"), headers=headers
    )
    product_id = create_resp.json()["data"]["id"]
    await client.patch(f"/api/v1/products/{product_id}", json={"status": "active"}, headers=headers)

    denied_resp = await client.delete(f"/api/v1/products/{product_id}", headers=headers)
    assert denied_resp.status_code == 409

    await client.post(f"/api/v1/products/{product_id}/archive", headers=headers)
    await client.post(f"/api/v1/products/{product_id}/restore", headers=headers)
    allowed_resp = await client.delete(f"/api/v1/products/{product_id}", headers=headers)
    assert allowed_resp.status_code == 200


@pytest.mark.asyncio
async def test_list_products_search_and_filter(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    await client.post("/api/v1/products", json=_product_payload("SC-700"), headers=headers)
    other = _product_payload("SC-701")
    other["name"] = "Totally Different Widget"
    other["target_industries"] = ["Healthcare"]
    await client.post("/api/v1/products", json=other, headers=headers)

    search_resp = await client.get("/api/v1/products?search=Acme", headers=headers)
    assert search_resp.status_code == 200
    items = search_resp.json()["data"]["items"]
    assert all("Acme" in item["name"] for item in items)

    industry_resp = await client.get("/api/v1/products?industry=Healthcare", headers=headers)
    industry_items = industry_resp.json()["data"]["items"]
    assert len(industry_items) == 1
    assert industry_items[0]["code"] == "SC-701"


@pytest.mark.asyncio
async def test_products_are_tenant_isolated(client, unique_email):
    headers_a = await _auth_headers(client, unique_email)
    await client.post("/api/v1/products", json=_product_payload("SC-800"), headers=headers_a)

    headers_b = await _auth_headers(client, f"b-{unique_email}")
    list_resp = await client.get("/api/v1/products", headers=headers_b)
    assert list_resp.json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_reindex_queues_embedding(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    create_resp = await client.post(
        "/api/v1/products", json=_product_payload("SC-900"), headers=headers
    )
    product_id = create_resp.json()["data"]["id"]

    reindex_resp = await client.post(f"/api/v1/products/{product_id}/reindex", headers=headers)
    assert reindex_resp.status_code == 200
    assert reindex_resp.json()["data"]["embedding_status"] == "queued"


@pytest.mark.asyncio
async def test_list_categories_returns_seeded_defaults(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    resp = await client.get("/api/v1/products/categories", headers=headers)
    assert resp.status_code == 200
    names = {c["name"] for c in resp.json()["data"]}
    assert "CRM & Sales" in names


@pytest.mark.asyncio
async def test_read_only_role_cannot_create_product(client, db_session, unique_email):
    admin_headers = await _auth_headers(client, unique_email)

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
    read_only_headers = {"Authorization": f"Bearer {login_resp.json()['data']['access_token']}"}

    create_resp = await client.post(
        "/api/v1/products", json=_product_payload("SC-RO-1"), headers=read_only_headers
    )
    assert create_resp.status_code == 403
    assert create_resp.json()["error"]["code"] == "PERMISSION_DENIED"

    # read-only can still view what an admin creates
    admin_create = await client.post(
        "/api/v1/products", json=_product_payload("SC-RO-2"), headers=admin_headers
    )
    view_resp = await client.get(
        f"/api/v1/products/{admin_create.json()['data']['id']}", headers=read_only_headers
    )
    assert view_resp.status_code == 200


@pytest.mark.asyncio
async def test_org_admin_cannot_create_category(client, unique_email):
    """Category creation is a platform-superadmin action, not an org.admin one — the global
    taxonomy is shared across every tenant, so no single org's admin should be able to add to
    it, even though org_admin otherwise holds every products.* permission."""
    headers = await _auth_headers(client, unique_email)
    resp = await client.post(
        "/api/v1/products/categories",
        json={"name": "Totally New Category"},
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_product_with_unknown_category_rejected(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    payload = _product_payload("SC-CAT-1") | {"category_id": "00000000-0000-0000-0000-000000000000"}
    resp = await client.post("/api/v1/products", json=payload, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_mock_embedding_provider_is_deterministic():
    provider = MockEmbeddingProvider()

    class FakeProduct:
        name = "Acme Sales Copilot"
        short_description = "AI assistant"
        detailed_description = ""
        target_industries: list[str] = []
        business_problems: list[str] = []
        key_features: list[str] = []
        benefits: list[str] = []
        ideal_customer_profile = ""
        common_use_cases: list[str] = []

    text = compose_embedding_text(FakeProduct())
    assert "Acme Sales Copilot" in text

    import asyncio

    vector_a = asyncio.run(provider.embed(text))
    vector_b = asyncio.run(provider.embed(text))
    assert vector_a == vector_b
    assert len(vector_a) == provider.dimensions
