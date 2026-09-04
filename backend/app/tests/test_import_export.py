import io
import uuid

import pytest

from app.core.storage import build_import_storage_key, get_file_storage
from app.models.import_job import ImportEntityType, ImportJob, ImportJobStatus
from app.workers import import_tasks


def _register_payload(org_name: str, email: str) -> dict:
    return {
        "organization_name": org_name,
        "admin_full_name": "Org Admin",
        "admin_email": email,
        "admin_password": "SuperSecret123",
    }


async def _auth(client, unique_email, org_name: str = "Acme Inc") -> tuple[str, str]:
    resp = await client.post(
        "/api/v1/auth/register", json=_register_payload(org_name, unique_email)
    )
    data = resp.json()["data"]
    return data["access_token"], data["organization_id"]


def _csv_file(text: str, filename: str = "import.csv"):
    return {"file": (filename, io.BytesIO(text.encode("utf-8")), "text/csv")}


COMPANY_CSV_HEADER = "name,website,industry,locations,company_size,confidence_score\n"


async def _create_company(client, headers, website: str = "https://acme.com") -> str:
    resp = await client.post(
        "/api/v1/companies",
        json={"name": "Acme Robotics", "website": website},
        headers=headers,
    )
    return resp.json()["data"]["id"]


async def _create_product(client, headers, code: str = "SC-100") -> str:
    resp = await client.post(
        "/api/v1/products",
        json={
            "name": "Acme Sales Copilot",
            "code": code,
            "short_description": "AI assistant",
            "detailed_description": "detail",
        },
        headers=headers,
    )
    return resp.json()["data"]["id"]


async def _run_pipeline_for_job(db_session, job: ImportJob) -> str:
    db_session.add(job)
    await db_session.commit()
    job_id = str(job.id)  # captured before expiring below — job.id itself becomes unsafe to
    # access synchronously afterward (see test_research_jobs.py for the same pattern)
    await import_tasks._run_import_async(job_id)
    db_session.expire_all()
    return job_id


async def _store_csv(organization_id: uuid.UUID, text: str, filename: str = "import.csv") -> str:
    storage = get_file_storage()
    key = build_import_storage_key(organization_id=organization_id, filename=filename)
    await storage.save(key=key, content=text.encode("utf-8"))
    return key


async def _first_member_id(client, headers) -> str:
    resp = await client.get("/api/v1/organizations/me/members", headers=headers)
    return resp.json()["data"][0]["user_id"]


@pytest.mark.asyncio
async def test_preview_company_import_valid(client, unique_email):
    token, _ = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    csv_text = COMPANY_CSV_HEADER + "Acme Robotics,https://acme.com,Robotics,SF;NYC,51-200,70\n"

    resp = await client.post(
        "/api/v1/imports/company/preview", files=_csv_file(csv_text), headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["can_proceed"] is True
    assert body["total_rows"] == 1
    assert body["valid_row_count"] == 1
    assert body["missing_required_columns"] == []


@pytest.mark.asyncio
async def test_preview_import_flags_missing_required_columns(client, unique_email):
    token, _ = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    csv_text = "name,industry\nAcme Robotics,Robotics\n"

    resp = await client.post(
        "/api/v1/imports/company/preview", files=_csv_file(csv_text), headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["can_proceed"] is False
    assert "website" in body["missing_required_columns"]


@pytest.mark.asyncio
async def test_start_import_queues_job_and_is_listed(client, unique_email):
    token, _ = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    csv_text = COMPANY_CSV_HEADER + "Acme Robotics,https://acme.com,Robotics,SF,51-200,70\n"

    resp = await client.post("/api/v1/imports/company", files=_csv_file(csv_text), headers=headers)
    assert resp.status_code == 202, resp.text
    job = resp.json()["data"]
    assert job["status"] == "queued"
    assert job["entity_type"] == "company"
    assert job["total_rows"] == 1

    list_resp = await client.get("/api/v1/imports", headers=headers)
    assert list_resp.json()["data"]["items"][0]["id"] == job["id"]

    get_resp = await client.get(f"/api/v1/imports/{job['id']}", headers=headers)
    assert get_resp.status_code == 200


@pytest.mark.asyncio
async def test_start_import_rejects_missing_required_columns(client, unique_email):
    token, _ = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    csv_text = "name,industry\nAcme Robotics,Robotics\n"

    resp = await client.post("/api/v1/imports/company", files=_csv_file(csv_text), headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_start_import_rejects_non_csv_content_type(client, unique_email):
    token, _ = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("import.csv", io.BytesIO(b"not,real,csv"), "application/pdf")}
    resp = await client.post("/api/v1/imports/company", files=files, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_import_pipeline_creates_companies_and_skips_duplicates(
    client, db_session, unique_email
):
    token, org_id = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    await _create_company(client, headers, "https://existing.com")

    csv_text = (
        COMPANY_CSV_HEADER
        + "New Robotics,https://new-robotics.com,Robotics,SF,51-200,80\n"
        + "Existing Co,https://existing.com,Robotics,SF,51-200,50\n"
    )
    key = await _store_csv(uuid.UUID(org_id), csv_text)
    user_id = await _first_member_id(client, headers)
    job = ImportJob(
        organization_id=uuid.UUID(org_id),
        user_id=uuid.UUID(user_id),
        entity_type=ImportEntityType.COMPANY,
        status=ImportJobStatus.QUEUED,
        file_name="import.csv",
        storage_key=key,
        total_rows=2,
    )
    job_id = await _run_pipeline_for_job(db_session, job)

    get_resp = await client.get(f"/api/v1/imports/{job_id}", headers=headers)
    body = get_resp.json()["data"]
    assert body["status"] == "completed", body
    assert body["created_count"] == 1
    assert body["skipped_count"] == 1
    assert body["error_count"] == 0

    companies_resp = await client.get("/api/v1/companies?search=New Robotics", headers=headers)
    assert len(companies_resp.json()["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_import_pipeline_continues_after_early_duplicate_row(
    client, db_session, unique_email
):
    """Regression test: a duplicate/skip on an early row must not corrupt the shared session for
    rows processed afterward (a prior bug expired the ImportJob ORM object on rollback and then
    read one of its attributes synchronously on the next iteration, raising MissingGreenlet)."""
    token, org_id = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    await _create_company(client, headers, "https://already-here.com")

    csv_text = (
        COMPANY_CSV_HEADER
        + "Already Here,https://already-here.com,Robotics,SF,51-200,50\n"
        + "Brand New One,https://brand-new-one.com,Robotics,SF,51-200,60\n"
        + "Brand New Two,https://brand-new-two.com,Robotics,SF,51-200,70\n"
    )
    key = await _store_csv(uuid.UUID(org_id), csv_text)
    user_id = await _first_member_id(client, headers)
    job = ImportJob(
        organization_id=uuid.UUID(org_id),
        user_id=uuid.UUID(user_id),
        entity_type=ImportEntityType.COMPANY,
        status=ImportJobStatus.QUEUED,
        file_name="import.csv",
        storage_key=key,
        total_rows=3,
    )
    job_id = await _run_pipeline_for_job(db_session, job)

    get_resp = await client.get(f"/api/v1/imports/{job_id}", headers=headers)
    body = get_resp.json()["data"]
    assert body["status"] == "completed", body
    assert body["created_count"] == 2
    assert body["skipped_count"] == 1
    assert body["error_count"] == 0

    companies_resp = await client.get("/api/v1/companies?page_size=50", headers=headers)
    names = {c["name"] for c in companies_resp.json()["data"]["items"]}
    assert {"Brand New One", "Brand New Two"} <= names


@pytest.mark.asyncio
async def test_import_pipeline_reports_row_errors_without_aborting(
    client, db_session, unique_email
):
    token, org_id = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}

    csv_text = (
        COMPANY_CSV_HEADER
        + "Bad Row,https://bad-row.com,Robotics,SF,51-200,not-a-number\n"
        + "Good Row,https://good-row.com,Robotics,SF,51-200,60\n"
    )
    key = await _store_csv(uuid.UUID(org_id), csv_text)
    members = await client.get("/api/v1/organizations/me/members", headers=headers)
    user_id = members.json()["data"][0]["user_id"]
    job = ImportJob(
        organization_id=uuid.UUID(org_id),
        user_id=uuid.UUID(user_id),
        entity_type=ImportEntityType.COMPANY,
        status=ImportJobStatus.QUEUED,
        file_name="import.csv",
        storage_key=key,
        total_rows=2,
    )
    job_id = await _run_pipeline_for_job(db_session, job)

    get_resp = await client.get(f"/api/v1/imports/{job_id}", headers=headers)
    body = get_resp.json()["data"]
    assert body["created_count"] == 1
    assert body["error_count"] == 1
    assert body["row_errors"][0]["row"] == 2


@pytest.mark.asyncio
async def test_import_pipeline_creates_leads_via_natural_keys(client, db_session, unique_email):
    token, org_id = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    await _create_company(client, headers, "https://lead-import.com")
    await _create_product(client, headers, "LI-100")

    csv_text = (
        "company_website,product_code,contact_email,name,source,tags\n"
        "https://lead-import.com,LI-100,,Imported Lead,csv_import,hot;q3\n"
    )
    key = await _store_csv(uuid.UUID(org_id), csv_text)
    members = await client.get("/api/v1/organizations/me/members", headers=headers)
    user_id = members.json()["data"][0]["user_id"]
    job = ImportJob(
        organization_id=uuid.UUID(org_id),
        user_id=uuid.UUID(user_id),
        entity_type=ImportEntityType.LEAD,
        status=ImportJobStatus.QUEUED,
        file_name="import.csv",
        storage_key=key,
        total_rows=1,
    )
    job_id = await _run_pipeline_for_job(db_session, job)

    get_resp = await client.get(f"/api/v1/imports/{job_id}", headers=headers)
    body = get_resp.json()["data"]
    assert body["created_count"] == 1, body

    leads_resp = await client.get("/api/v1/leads?search=Imported Lead", headers=headers)
    items = leads_resp.json()["data"]["items"]
    assert len(items) == 1


@pytest.mark.asyncio
async def test_import_pipeline_lead_row_fails_for_unknown_company(client, db_session, unique_email):
    token, org_id = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    await _create_product(client, headers, "LI-200")

    csv_text = (
        "company_website,product_code,contact_email,name,source,tags\n"
        "https://does-not-exist.com,LI-200,,Orphan Lead,csv_import,\n"
    )
    key = await _store_csv(uuid.UUID(org_id), csv_text)
    members = await client.get("/api/v1/organizations/me/members", headers=headers)
    user_id = members.json()["data"][0]["user_id"]
    job = ImportJob(
        organization_id=uuid.UUID(org_id),
        user_id=uuid.UUID(user_id),
        entity_type=ImportEntityType.LEAD,
        status=ImportJobStatus.QUEUED,
        file_name="import.csv",
        storage_key=key,
        total_rows=1,
    )
    job_id = await _run_pipeline_for_job(db_session, job)

    get_resp = await client.get(f"/api/v1/imports/{job_id}", headers=headers)
    body = get_resp.json()["data"]
    assert body["error_count"] == 1
    assert "No company found" in body["row_errors"][0]["errors"][0]


@pytest.mark.asyncio
async def test_imports_are_tenant_isolated(client, unique_email):
    token_a, _ = await _auth(client, unique_email, "Org A")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    csv_text = COMPANY_CSV_HEADER + "Acme Robotics,https://acme-iso.com,Robotics,SF,51-200,70\n"
    resp = await client.post(
        "/api/v1/imports/company", files=_csv_file(csv_text), headers=headers_a
    )
    job_id = resp.json()["data"]["id"]

    token_b, _ = await _auth(client, f"b-{unique_email}", "Org B")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    get_resp = await client.get(f"/api/v1/imports/{job_id}", headers=headers_b)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_export_leads_csv_and_json(client, unique_email):
    token, _ = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    await client.post(
        "/api/v1/leads",
        json={
            "company_id": company_id,
            "product_id": product_id,
            "name": "Export Me",
            "source": "manual",
        },
        headers=headers,
    )

    csv_resp = await client.post("/api/v1/leads/export", json={"format": "csv"}, headers=headers)
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"].startswith("text/csv")
    assert "Export Me" in csv_resp.text
    assert not csv_resp.text.startswith("﻿")

    csv_excel_resp = await client.post(
        "/api/v1/leads/export", json={"format": "csv_excel"}, headers=headers
    )
    assert csv_excel_resp.content.decode("utf-8-sig").startswith("id,name")

    json_resp = await client.post("/api/v1/leads/export", json={"format": "json"}, headers=headers)
    assert json_resp.headers["content-type"].startswith("application/json")
    records = json_resp.json()
    assert len(records) == 1
    assert records[0]["name"] == "Export Me"
    assert records[0]["company_name"] == "Acme Robotics"


@pytest.mark.asyncio
async def test_export_leads_includes_linked_contact_details(client, unique_email):
    """A lead export is how a rep gets a shareable customer list — it must include the actual
    contact's name/title/email/phone, not just the internal assigned rep's name."""
    token, _ = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)

    contact_resp = await client.post(
        "/api/v1/contacts",
        json={
            "company_id": company_id,
            "full_name": "Jamie Rivera",
            "job_title": "VP of Engineering",
            "business_email": "jamie@acme.com",
            "business_phone": "+1-555-0100",
        },
        headers=headers,
    )
    contact_id = contact_resp.json()["data"]["id"]

    await client.post(
        "/api/v1/leads",
        json={
            "company_id": company_id,
            "product_id": product_id,
            "contact_id": contact_id,
            "name": "Export With Contact",
            "source": "manual",
        },
        headers=headers,
    )

    resp = await client.post("/api/v1/leads/export", json={"format": "json"}, headers=headers)
    record = next(r for r in resp.json() if r["name"] == "Export With Contact")
    assert record["contact_name"] == "Jamie Rivera"
    assert record["contact_job_title"] == "VP of Engineering"
    assert record["contact_email"] == "jamie@acme.com"
    assert record["contact_phone"] == "+1-555-0100"


@pytest.mark.asyncio
async def test_export_leads_respects_status_filter(client, unique_email):
    token, _ = await _auth(client, unique_email)
    headers = {"Authorization": f"Bearer {token}"}
    company_id = await _create_company(client, headers)
    product_id = await _create_product(client, headers)
    lead_resp = await client.post(
        "/api/v1/leads",
        json={
            "company_id": company_id,
            "product_id": product_id,
            "name": "Filtered Lead",
            "source": "manual",
        },
        headers=headers,
    )
    lead_id = lead_resp.json()["data"]["id"]
    await client.post(f"/api/v1/leads/{lead_id}/status", json={"status": "won"}, headers=headers)

    resp = await client.post(
        "/api/v1/leads/export", json={"format": "json", "status": "lost"}, headers=headers
    )
    assert resp.json() == []
