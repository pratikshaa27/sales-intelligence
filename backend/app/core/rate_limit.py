from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

# Disabled under APP_ENV=test: the test suite drives many requests from the same client
# address in quick succession, which would otherwise trip auth-endpoint rate limits and fail
# tests that have nothing to do with rate limiting (see app/tests/test_*.py).
limiter = Limiter(key_func=get_remote_address, enabled=get_settings().app_env != "test")
