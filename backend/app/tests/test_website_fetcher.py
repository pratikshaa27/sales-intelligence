import httpx
import pytest

from app.research import website_fetcher
from app.research.website_fetcher import WebsiteFetchError, fetch_website_text


def _patch_transport(monkeypatch, handler) -> None:
    """website_fetcher.py constructs its own httpx.AsyncClient internally, so the only way to
    inject a mock transport (and avoid a real network call) is to wrap the AsyncClient
    constructor it uses."""
    original_client = httpx.AsyncClient

    def _patched(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(website_fetcher.httpx, "AsyncClient", _patched)


@pytest.mark.asyncio
async def test_fetch_rejects_redirect_to_private_ip(monkeypatch):
    """The whole reason every redirect hop is re-validated (not just the initial URL): a
    public-looking URL can redirect to an internal address, which must still be blocked."""

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})
        raise AssertionError("Should never reach the redirect target")

    _patch_transport(monkeypatch, _handler)

    with pytest.raises(WebsiteFetchError):
        await fetch_website_text("https://example.com/")


@pytest.mark.asyncio
async def test_fetch_follows_redirect_to_safe_url(monkeypatch):
    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.com" and request.url.path == "/start":
            return httpx.Response(302, headers={"location": "https://example.com/final"})
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"<html><title>Final</title><body>Safe content</body></html>",
        )

    _patch_transport(monkeypatch, _handler)

    page = await fetch_website_text("https://example.com/start")
    assert page.title == "Final"
    assert "Safe content" in page.text


@pytest.mark.asyncio
async def test_fetch_rejects_non_html_content_type(monkeypatch):
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json"}, content=b"{}")

    _patch_transport(monkeypatch, _handler)

    with pytest.raises(WebsiteFetchError):
        await fetch_website_text("https://example.com/")
