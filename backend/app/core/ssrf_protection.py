"""SSRF protection for any feature that fetches a user- or AI-supplied URL (spec §20): blocks
localhost, private/reserved/link-local IP ranges, cloud metadata endpoints, and non-http(s)
schemes. Validates the *resolved* IP, not just the hostname string, so a DNS name that resolves
to an internal address is caught too — and callers must re-validate on every redirect hop, since
a safe URL can redirect to an unsafe one.
"""

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}

# 169.254.169.254 is the cloud metadata endpoint on AWS/GCP/Azure/etc; it's link-local so
# is_link_local already covers it, but it's called out explicitly for clarity/documentation.
CLOUD_METADATA_IP = "169.254.169.254"

BLOCKED_HOSTNAMES = {"localhost", "metadata", "metadata.google.internal"}


class SSRFError(Exception):
    """Raised when a URL is not safe to fetch server-side."""


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparsable "IP" is not safe to trust
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_url_is_safe(url: str) -> str:
    """Raise SSRFError if `url` is not safe to fetch. Returns the normalized hostname on success.

    Callers MUST call this again for every redirect hop before following it — validating only
    the original URL is not sufficient, since a public URL can redirect to an internal one.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SSRFError(f"Unsupported URL scheme '{parsed.scheme}'; only http/https are allowed")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("URL has no hostname")

    hostname_lower = hostname.lower()
    if hostname_lower in BLOCKED_HOSTNAMES:
        raise SSRFError(f"Host '{hostname}' is not allowed")

    # A literal IP in the URL: validate directly.
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None
    if literal_ip is not None:
        if _is_blocked_ip(str(literal_ip)):
            raise SSRFError(f"IP address '{hostname}' is not allowed")
        return hostname_lower

    # A DNS name: resolve it and validate every returned address (protects against a name that
    # resolves to a private/internal address, and against DNS rebinding using the first result).
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except OSError as exc:
        raise SSRFError(f"Could not resolve host '{hostname}'") from exc

    resolved_ips = {info[4][0] for info in addr_infos}
    if not resolved_ips:
        raise SSRFError(f"Could not resolve host '{hostname}'")
    for ip_str in resolved_ips:
        if _is_blocked_ip(ip_str):
            raise SSRFError(f"Host '{hostname}' resolves to a disallowed address")

    return hostname_lower
