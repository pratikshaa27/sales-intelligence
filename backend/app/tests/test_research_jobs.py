import uuid
from collections.abc import Coroutine

import pytest

from app.models.research import JobType, ResearchJob
from app.research.website_fetcher import WebsiteFetchError, WebsitePage
from app.workers import research_tasks


async def _run_pipeline(coro: Coroutine) -> None:
    await coro


def _register_payload(org_name: str, email: str) -> dict:
    return {
        "organization_name": org_name,
        "admin_full_name": "Org Admin",
        "admin_email": email,
        "admin_password": "SuperSecret123",
    }


async def _auth_headers(client, unique_email, org_name: str = "Acme Inc") -> tuple[str, str]:
    resp = await client.post(
        "/api/v1/auth/register", json=_register_payload(org_name, unique_email)
    )
    token = resp.json()["data"]["access_token"]
    return token, resp.json()["data"]["organization_id"]


async def _create_company(client, token, website: str = "https://acme.com") -> str:
    resp = await client.post(
        "/api/v1/companies",
        json={"name": "Acme Robotics", "website": website},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["data"]["id"]


@pytest.mark.asyncio
async def test_research_endpoint_queues_job(client, unique_email):
    token, _ = await _auth_headers(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    company_id = await _create_company(client, token)

    resp = await client.post(f"/api/v1/companies/{company_id}/research", headers=headers)
    assert resp.status_code == 202, resp.text
    body = resp.json()["data"]
    assert body["job_type"] == "company_research"
    assert body["status"] == "queued"

    list_resp = await client.get("/api/v1/jobs", headers=headers)
    assert list_resp.json()["data"]["items"][0]["id"] == body["id"]


@pytest.mark.asyncio
async def test_discover_endpoint_queues_job(client, unique_email):
    token, _ = await _auth_headers(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/companies/discover",
        json={"industry": "Robotics", "keywords": ["automation"], "number_of_companies": 3},
        headers=headers,
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["data"]["job_type"] == "company_discovery"


@pytest.mark.asyncio
async def test_cancel_job_rejects_already_terminal_job(client, unique_email):
    token, _ = await _auth_headers(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    company_id = await _create_company(client, token)
    resp = await client.post(f"/api/v1/companies/{company_id}/research", headers=headers)
    job_id = resp.json()["data"]["id"]

    first_cancel = await client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
    assert first_cancel.status_code == 200
    assert first_cancel.json()["data"]["status"] == "cancelled"

    second_cancel = await client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
    assert second_cancel.status_code == 409


@pytest.mark.asyncio
async def test_company_research_pipeline_end_to_end(client, db_session, unique_email, monkeypatch):
    """Exercises the full pipeline (website fetch -> AI extraction -> evidence -> company merge
    -> job completion) by calling the worker function directly, with the website fetch
    monkeypatched so the test never makes a real network call."""
    token, org_id = await _auth_headers(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    company_id = await _create_company(client, token)

    fake_page = WebsitePage(
        final_url="https://acme.com/",
        title="Acme Robotics — Home",
        meta_description="Industrial robots for modern factories.",
        text=(
            "Acme Robotics builds industrial robots. We use AWS and Kubernetes to run our fleet "
            "management platform. We're hiring across engineering — join our team! We recently "
            "opened a new office to support expanding into new markets."
        ),
    )

    async def _fake_fetch(url: str) -> WebsitePage:
        return fake_page

    monkeypatch.setattr(research_tasks, "fetch_website_text", _fake_fetch)

    job = ResearchJob(
        organization_id=uuid.UUID(org_id),
        job_type=JobType.COMPANY_RESEARCH,
        input_parameters={"company_id": company_id},
    )
    db_session.add(job)
    await db_session.commit()
    job_id = str(job.id)  # captured before expiring below — job.id itself becomes unsafe to
    # access afterward (see comment on expire_all())

    await _run_pipeline(research_tasks._run_company_research_async(job_id))
    # The pipeline commits through its own separate session/connection; db_session's identity
    # map still holds the pre-pipeline (queued) copy of `job` from when this test created it, so
    # it must be expired before any further read through db_session (including the client's
    # HTTP calls below, which reuse db_session via the get_db override) sees the fresh state.
    # Note: this makes every attribute on `job` itself unsafe to access synchronously (e.g. in
    # an f-string) afterward, since that would trigger an implicit lazy-load outside of any
    # `await` — hence capturing job_id as a plain str above instead of using job.id below.
    db_session.expire_all()

    get_resp = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    job_body = get_resp.json()["data"]
    assert job_body["status"] == "completed", job_body
    assert job_body["result_summary"]["evidence_created"] > 0

    company_resp = await client.get(f"/api/v1/companies/{company_id}", headers=headers)
    company_body = company_resp.json()["data"]
    assert company_body["research_status"] == "researched"
    assert "AWS" in company_body["technology_stack"]
    assert company_body["confidence_score"] > 0
    assert company_body["business_description"]

    evidence_resp = await client.get(f"/api/v1/companies/{company_id}/evidence", headers=headers)
    evidence = evidence_resp.json()["data"]
    assert len(evidence) == job_body["result_summary"]["evidence_created"]
    assert all(e["source_url"] == "https://acme.com/" for e in evidence)
    assert all(e["is_ai_generated"] for e in evidence)

    sources_resp = await client.get(f"/api/v1/companies/{company_id}/sources", headers=headers)
    assert any(s["url"] == "https://acme.com/" for s in sources_resp.json()["data"])


@pytest.mark.asyncio
async def test_company_research_pipeline_handles_fetch_failure(
    client, db_session, unique_email, monkeypatch
):
    token, org_id = await _auth_headers(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    company_id = await _create_company(client, token)

    async def _fake_fetch_fails(url: str) -> WebsitePage:
        raise WebsiteFetchError("Host resolves to a disallowed address")

    monkeypatch.setattr(research_tasks, "fetch_website_text", _fake_fetch_fails)

    job = ResearchJob(
        organization_id=uuid.UUID(org_id),
        job_type=JobType.COMPANY_RESEARCH,
        input_parameters={"company_id": company_id},
    )
    db_session.add(job)
    await db_session.commit()
    job_id = str(job.id)

    await _run_pipeline(research_tasks._run_company_research_async(job_id))
    db_session.expire_all()

    get_resp = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    job_body = get_resp.json()["data"]
    assert job_body["status"] == "failed"
    assert "disallowed address" in job_body["error_message"]


@pytest.mark.asyncio
async def test_company_discovery_pipeline_marks_mock_data(client, db_session, unique_email):
    token, org_id = await _auth_headers(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}

    job = ResearchJob(
        organization_id=uuid.UUID(org_id),
        job_type=JobType.COMPANY_DISCOVERY,
        input_parameters={
            "industry": "Robotics",
            "location": "",
            "company_size": "",
            "keywords": ["automation"],
            "number_of_companies": 3,
        },
    )
    db_session.add(job)
    await db_session.commit()
    job_id = str(job.id)

    await _run_pipeline(research_tasks._run_company_discovery_async(job_id))
    db_session.expire_all()

    get_resp = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    job_body = get_resp.json()["data"]
    assert job_body["status"] == "completed"
    assert job_body["result_summary"]["is_mock_data"] is True
    assert len(job_body["result_summary"]["candidates"]) == 3
    for candidate in job_body["result_summary"]["candidates"]:
        assert "[MOCK DATA" in candidate["rationale"]


@pytest.mark.asyncio
async def test_research_jobs_are_tenant_isolated(client, unique_email):
    token_a, _ = await _auth_headers(client, unique_email, "Org A")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    company_id = await _create_company(client, token_a)
    resp = await client.post(f"/api/v1/companies/{company_id}/research", headers=headers_a)
    job_id = resp.json()["data"]["id"]

    token_b, _ = await _auth_headers(client, f"b-{unique_email}", "Org B")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    get_resp = await client.get(f"/api/v1/jobs/{job_id}", headers=headers_b)
    assert get_resp.status_code == 404
