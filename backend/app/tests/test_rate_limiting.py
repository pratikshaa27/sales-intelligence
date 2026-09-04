import uuid

import pytest

from app.core.rate_limit import limiter


@pytest.mark.asyncio
async def test_register_endpoint_enforces_rate_limit(client, monkeypatch):
    """Rate limiting is disabled under APP_ENV=test (see app/core/rate_limit.py) so the rest of
    the suite isn't flaky from firing several requests in quick succession — this test
    re-enables it just for itself to prove the limit is actually wired up on /auth/register."""
    monkeypatch.setattr(limiter, "enabled", True)

    responses = []
    for _ in range(6):  # the route is decorated @limiter.limit("5/minute")
        email = f"rl-{uuid.uuid4().hex[:10]}@example.com"
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "Rate Limit Test Org",
                "admin_full_name": "Org Admin",
                "admin_email": email,
                "admin_password": "SuperSecret123",
            },
        )
        responses.append(resp.status_code)

    assert responses[:5] == [201, 201, 201, 201, 201]
    assert responses[5] == 429
