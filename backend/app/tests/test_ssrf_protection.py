import pytest

from app.core.ssrf_protection import SSRFError, validate_url_is_safe


def test_allows_public_https_url():
    # example.com is IANA-reserved for documentation/testing and always resolves to a public IP.
    validate_url_is_safe("https://example.com/about")


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://127.0.0.1/",
        "http://127.0.0.1:8000/admin",
        "http://[::1]/",
        "http://10.0.0.5/",
        "http://172.16.0.5/",
        "http://192.168.1.5/",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata endpoint
        "http://0.0.0.0/",
    ],
)
def test_blocks_private_and_loopback_addresses(url):
    with pytest.raises(SSRFError):
        validate_url_is_safe(url)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/",
        "gopher://example.com/",
    ],
)
def test_blocks_disallowed_schemes(url):
    with pytest.raises(SSRFError):
        validate_url_is_safe(url)


def test_blocks_url_with_no_hostname():
    with pytest.raises(SSRFError):
        validate_url_is_safe("http:///path-only")


def test_blocks_unresolvable_hostname():
    with pytest.raises(SSRFError):
        validate_url_is_safe("http://this-domain-should-not-exist-12345.invalid/")
