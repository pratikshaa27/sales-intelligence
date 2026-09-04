"""Fetches a single public webpage for research purposes (spec §4.5: "Public Research"), with
SSRF protection (spec §20) applied to the initial URL and to every redirect hop — a safe URL can
redirect to an unsafe one, so re-validating only once would be a bypass.
"""

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.ssrf_protection import SSRFError, validate_url_is_safe

USER_AGENT = "SalesIntelligencePlatformBot/1.0 (+company research; see platform docs)"
MAX_TEXT_LENGTH = 20_000


class WebsiteFetchError(Exception):
    pass


@dataclass
class WebsitePage:
    final_url: str
    title: str
    meta_description: str
    text: str


def _extract_page(html: str, final_url: str) -> WebsitePage:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = meta_tag["content"].strip()

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    raw_text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", raw_text).strip()[:MAX_TEXT_LENGTH]

    return WebsitePage(
        final_url=final_url, title=title, meta_description=meta_description, text=text
    )


async def fetch_website_text(url: str) -> WebsitePage:
    settings = get_settings()
    current_url = url
    redirects_followed = 0

    async with httpx.AsyncClient(
        follow_redirects=False, timeout=settings.website_fetch_timeout_seconds
    ) as client:
        while True:
            try:
                validate_url_is_safe(current_url)
            except SSRFError as exc:
                raise WebsiteFetchError(str(exc)) from exc

            try:
                async with client.stream(
                    "GET", current_url, headers={"User-Agent": USER_AGENT}
                ) as response:
                    if response.is_redirect:
                        redirects_followed += 1
                        if redirects_followed > settings.website_fetch_max_redirects:
                            raise WebsiteFetchError("Too many redirects")
                        location = response.headers.get("location")
                        if not location:
                            raise WebsiteFetchError("Redirect response missing Location header")
                        current_url = str(httpx.URL(current_url).join(location))
                        continue

                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type:
                        raise WebsiteFetchError(f"Unsupported content type '{content_type}'")

                    # Stream with a hard cap: httpx.get() would buffer the entire body first,
                    # which defeats a size limit against a huge or slow-drip response.
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) >= settings.website_fetch_max_bytes:
                            break
                    content = bytes(chunks[: settings.website_fetch_max_bytes])
                    encoding = response.encoding or "utf-8"
                    final_url = str(response.url)
            except httpx.HTTPError as exc:
                raise WebsiteFetchError(f"Request failed: {exc}") from exc

            break

        html = content.decode(encoding, errors="replace")
        return _extract_page(html, final_url)
