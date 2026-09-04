import io

import pytest


def _register_payload(org_name: str, email: str) -> dict:
    return {
        "organization_name": org_name,
        "admin_full_name": "Org Admin",
        "admin_email": email,
        "admin_password": "SuperSecret123",
    }


async def _auth_headers(client, unique_email) -> dict:
    resp = await client.post(
        "/api/v1/auth/register", json=_register_payload("Acme Inc", unique_email)
    )
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


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


@pytest.mark.asyncio
async def test_upload_document_accepts_a_real_pdf(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    product_id = await _create_product(client, headers)

    pdf_bytes = b"%PDF-1.4\n%mock pdf content\n"
    files = {"file": ("spec.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    resp = await client.post(
        f"/api/v1/products/{product_id}/documents", files=files, headers=headers
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["content_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_upload_document_rejects_spoofed_content_type(client, unique_email):
    """A file claiming to be a PDF via its Content-Type header but whose actual bytes don't
    match the PDF magic number must be rejected — the header alone isn't trustworthy."""
    headers = await _auth_headers(client, unique_email)
    product_id = await _create_product(client, headers)

    fake_pdf = b"MZ\x90\x00this is actually an executable, not a pdf"
    files = {"file": ("not-a-pdf.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    resp = await client.post(
        f"/api/v1/products/{product_id}/documents", files=files, headers=headers
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_document_rejects_disallowed_content_type(client, unique_email):
    headers = await _auth_headers(client, unique_email)
    product_id = await _create_product(client, headers)

    files = {"file": ("script.exe", io.BytesIO(b"MZ\x90\x00"), "application/x-msdownload")}
    resp = await client.post(
        f"/api/v1/products/{product_id}/documents", files=files, headers=headers
    )
    assert resp.status_code == 422
