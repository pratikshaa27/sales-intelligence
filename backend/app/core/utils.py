import re
import uuid
from urllib.parse import urlparse

from fastapi import Request


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "org"


def unique_slug_candidate(base_slug: str) -> str:
    return f"{base_slug}-{uuid.uuid4().hex[:6]}"


def normalize_domain(raw: str) -> str:
    """Reduce a website URL or bare domain to a canonical form for dedup (spec §4.4): lowercase,
    no scheme, no "www.", no path/query/port. "https://www.Acme.com/about?x=1" -> "acme.com"."""
    value = raw.strip().lower()
    if not value:
        return ""
    if "//" not in value:
        value = f"//{value}"
    parsed = urlparse(value)
    host = parsed.netloc or parsed.path
    host = host.split("/")[0].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""
