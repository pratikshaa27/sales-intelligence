import pytest


def _register_payload(org_name: str, email: str) -> dict:
    return {
        "organization_name": org_name,
        "admin_full_name": "Org Admin",
        "admin_email": email,
        "admin_password": "SuperSecret123",
    }


@pytest.mark.asyncio
async def test_org_a_cannot_see_org_b_members(client, unique_email):
    email_a = unique_email
    email_b = f"b-{unique_email}"

    resp_a = await client.post("/api/v1/auth/register", json=_register_payload("Org A", email_a))
    token_a = resp_a.json()["data"]["access_token"]

    resp_b = await client.post("/api/v1/auth/register", json=_register_payload("Org B", email_b))
    org_b_id = resp_b.json()["data"]["organization_id"]

    members_a = await client.get(
        "/api/v1/organizations/me/members", headers={"Authorization": f"Bearer {token_a}"}
    )
    emails_a = {m["email"] for m in members_a.json()["data"]}
    assert email_b.lower() not in emails_a

    # Org A's token must never grant access to Org B's data even for org-scoped GET /me,
    # since organization_id is derived server-side from the JWT, never from client input.
    org_a_view = await client.get(
        "/api/v1/organizations/me", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert org_a_view.json()["data"]["id"] != org_b_id


@pytest.mark.asyncio
async def test_access_token_from_org_a_rejected_without_valid_signature(client, unique_email):
    resp_a = await client.post(
        "/api/v1/auth/register", json=_register_payload("Org C", unique_email)
    )
    token = resp_a.json()["data"]["access_token"]
    # Flip a character in the middle of the signature rather than the very last one: the
    # last base64url character of a JWT only encodes a few significant bits (the rest is
    # padding), so some substitutions there decode to the same bytes and wouldn't actually
    # tamper the signature — see RFC 4648 base64 padding.
    mid = len(token) // 2
    tampered = token[:mid] + ("A" if token[mid] != "A" else "B") + token[mid + 1 :]

    resp = await client.get(
        "/api/v1/organizations/me", headers={"Authorization": f"Bearer {tampered}"}
    )
    assert resp.status_code == 401
