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


def _contact_payload(company_id: str) -> dict:
    return {
        "company_id": company_id,
        "full_name": "Jamie Rivera",
        "job_title": "VP of Engineering",
        "seniority": "VP",
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
    resp = await client.post("/api/v1/products", json=_product_payload(code), headers=headers)
    return resp.json()["data"]["id"]


async def _create_contact(client, headers, company_id: str) -> str:
    resp = await client.post("/api/v1/contacts", json=_contact_payload(company_id), headers=headers)
    return resp.json()["data"]["id"]


async def _create_lead(client, headers, company_id: str, product_id: str, **overrides) -> dict:
    payload = {
        "company_id": company_id,
        "product_id": product_id,
        "name": "Acme Robotics - Sales Copilot",
        "source": "manual",
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/leads", json=payload, headers=headers)
    return resp


@pytest.mark.asyncio
async def test_create_lead_computes_transparent_score(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    contact_id = await _create_contact(client, headers, company_id)

    resp = await _create_lead(client, headers, company_id, product_id, contact_id=contact_id)
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    assert body["status"] == "new"
    assert body["total_score"] == (
        body["fit_score"]
        + body["need_score"]
        + body["authority_score"]
        + body["timing_score"]
        + body["data_confidence_score"]
    )

    scores_resp = await client.get(f"/api/v1/leads/{body['id']}/scores", headers=headers)
    scores = scores_resp.json()["data"]
    assert len(scores) == 1
    assert scores[0]["reasons"], "score must carry human-readable reasons, not a bare number"


@pytest.mark.asyncio
async def test_create_lead_rejects_unknown_company(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    product_id = await _create_product(client, headers)
    resp = await _create_lead(client, headers, "00000000-0000-0000-0000-000000000000", product_id)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_recalculate_score_appends_new_score_row(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead_id = (await _create_lead(client, headers, company_id, product_id)).json()["data"]["id"]

    resp = await client.post(f"/api/v1/leads/{lead_id}/recalculate-score", headers=headers)
    assert resp.status_code == 200

    scores_resp = await client.get(f"/api/v1/leads/{lead_id}/scores", headers=headers)
    assert len(scores_resp.json()["data"]) == 2


@pytest.mark.asyncio
async def test_status_transition_and_activity_log(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead_id = (await _create_lead(client, headers, company_id, product_id)).json()["data"]["id"]

    resp = await client.post(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": "qualified", "reason": "Meets ICP"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "qualified"

    same_status_resp = await client.post(
        f"/api/v1/leads/{lead_id}/status", json={"status": "qualified"}, headers=headers
    )
    assert same_status_resp.status_code == 422

    activities_resp = await client.get(f"/api/v1/leads/{lead_id}/activities", headers=headers)
    activity_types = [a["activity_type"] for a in activities_resp.json()["data"]]
    assert "created" in activity_types
    assert "score_recalculated" in activity_types
    assert "status_changed" in activity_types


@pytest.mark.asyncio
async def test_assign_lead_to_member_moves_to_assigned_status(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead_id = (await _create_lead(client, headers, company_id, product_id)).json()["data"]["id"]

    members_resp = await client.get("/api/v1/organizations/me/members", headers=headers)
    user_id = members_resp.json()["data"][0]["user_id"]

    resp = await client.post(
        f"/api/v1/leads/{lead_id}/assign", json={"assigned_to": user_id}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["assigned_to"] == user_id
    assert resp.json()["data"]["status"] == "assigned"


@pytest.mark.asyncio
async def test_assign_lead_rejects_non_member(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead_id = (await _create_lead(client, headers, company_id, product_id)).json()["data"]["id"]

    resp = await client.post(
        f"/api/v1/leads/{lead_id}/assign",
        json={"assigned_to": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_generate_brief_includes_disclaimer_and_no_fabricated_claims(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    contact_id = await _create_contact(client, headers, company_id)
    lead_id = (
        await _create_lead(client, headers, company_id, product_id, contact_id=contact_id)
    ).json()["data"]["id"]

    resp = await client.post(f"/api/v1/leads/{lead_id}/brief", headers=headers)
    assert resp.status_code == 201, resp.text
    brief = resp.json()["data"]
    assert brief["disclaimer"]
    assert brief["ai_provider"] == "mock"
    assert brief["suggested_opener"]
    assert brief["discovery_questions"]

    list_resp = await client.get(f"/api/v1/leads/{lead_id}/briefs", headers=headers)
    assert len(list_resp.json()["data"]) == 1


@pytest.mark.asyncio
async def test_brief_does_not_quote_raw_overview_evidence(client, db_session, unique_email):
    """The 'overview' evidence category is a raw, truncated homepage-text snippet (real websites
    often put nav-menu/cookie-banner text in the first ~280 chars) — it should never be quoted
    verbatim in a generated discovery question, only genuine extracted facts/signals should be."""
    import datetime

    from app.models.research import EvidenceCategory, ResearchEvidence
    from app.repositories.company_repository import CompanyRepository

    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead_id = (await _create_lead(client, headers, company_id, product_id)).json()["data"]["id"]

    org_id = (await client.get("/api/v1/organizations/me", headers=headers)).json()["data"]["id"]
    company = await CompanyRepository(db_session).get_by_id(
        organization_id=org_id, company_id=company_id
    )
    now = datetime.datetime.now(datetime.UTC)
    db_session.add_all(
        [
            ResearchEvidence(
                organization_id=org_id,
                company_id=company.id,
                category=EvidenceCategory.OVERVIEW,
                fact_text="Skip to Main content Keyboard shortcuts Search alt + / — noisy nav text",
                source_url="https://acme.com",
                retrieved_at=now,
            ),
            ResearchEvidence(
                organization_id=org_id,
                company_id=company.id,
                category=EvidenceCategory.BUSINESS_CHALLENGE,
                fact_text="Scaling manufacturing operations across three new facilities",
                source_url="https://acme.com/about",
                retrieved_at=now,
            ),
        ]
    )
    await db_session.commit()

    resp = await client.post(f"/api/v1/leads/{lead_id}/brief", headers=headers)
    assert resp.status_code == 201, resp.text
    questions = " ".join(resp.json()["data"]["discovery_questions"]).lower()
    assert "skip to main content" not in questions
    assert "scaling manufacturing operations" in questions


@pytest.mark.asyncio
async def test_notes_crud(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead_id = (await _create_lead(client, headers, company_id, product_id)).json()["data"]["id"]

    add_resp = await client.post(
        f"/api/v1/leads/{lead_id}/notes",
        json={"body": "Spoke with VP, interested"},
        headers=headers,
    )
    assert add_resp.status_code == 201

    list_resp = await client.get(f"/api/v1/leads/{lead_id}/notes", headers=headers)
    assert len(list_resp.json()["data"]) == 1
    assert list_resp.json()["data"][0]["body"] == "Spoke with VP, interested"


@pytest.mark.asyncio
async def test_product_match_suggestions_ranked_by_projected_score(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    good_product_id = await _create_product(client, headers, "SC-200")
    await client.patch(
        f"/api/v1/products/{good_product_id}", json={"status": "active"}, headers=headers
    )

    mismatched = _product_payload("SC-201")
    mismatched["target_industries"] = ["Retail"]
    mismatched["target_company_size"] = ["1-10"]
    mismatched["target_geographic_regions"] = ["Nowhere"]
    mismatched["business_problems"] = ["Unrelated problem"]
    mismatched["supported_integrations"] = []
    bad_resp = await client.post("/api/v1/products", json=mismatched, headers=headers)
    bad_product_id = bad_resp.json()["data"]["id"]
    await client.patch(
        f"/api/v1/products/{bad_product_id}", json={"status": "active"}, headers=headers
    )

    resp = await client.get(
        f"/api/v1/leads/product-matches?company_id={company_id}", headers=headers
    )
    assert resp.status_code == 200, resp.text
    suggestions = resp.json()["data"]
    assert suggestions[0]["product_id"] == good_product_id
    assert suggestions[0]["projected_total_score"] >= suggestions[-1]["projected_total_score"]


@pytest.mark.asyncio
async def test_leads_are_tenant_isolated(client, unique_email):
    headers_a = await _auth_headers(client, unique_email, "Org A")
    company_id = await _create_company(client, headers_a)
    product_id = await _create_product(client, headers_a)
    await _create_lead(client, headers_a, company_id, product_id)

    headers_b = await _auth_headers(client, f"b-{unique_email}", "Org B")
    list_resp = await client.get("/api/v1/leads", headers=headers_b)
    assert list_resp.json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_delete_lead(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead_id = (await _create_lead(client, headers, company_id, product_id)).json()["data"]["id"]

    delete_resp = await client.delete(f"/api/v1/leads/{lead_id}", headers=headers)
    assert delete_resp.status_code == 200

    get_resp = await client.get(f"/api/v1/leads/{lead_id}", headers=headers)
    assert get_resp.status_code == 404
