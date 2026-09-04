import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.rate_limit import limiter

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

if settings.sentry_dsn:
    import sentry_sdk

    # Opt-in only: activates when SENTRY_DSN is set (spec §23 "monitoring and error tracking"),
    # a no-op otherwise so local dev/CI never depend on an external service.
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=0.1,
    )

_WEAK_JWT_SECRETS = {"change-me-in-env", ""}
if settings.is_production and (
    settings.jwt_secret_key in _WEAK_JWT_SECRETS or len(settings.jwt_secret_key) < 32
):
    # Fail fast at process startup rather than silently signing production tokens with a
    # default/guessable secret (spec §28 rule 18: "use secure defaults").
    raise RuntimeError(
        "JWT_SECRET_KEY must be set to a long random value in production — refusing to start "
        "with a default or short secret."
    )

app = FastAPI(
    title="AI-Powered Sales Intelligence Platform API",
    version="0.1.0",
    description="Backend API for the Sales Intelligence Platform.",
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {"code": "RATE_LIMITED", "message": "Too many requests", "details": {}},
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    # API-layer security headers (spec §20) — the frontend's Next.js config sets the
    # browser-rendering-relevant subset of these for its own pages; this covers the API
    # responses themselves, which the frontend headers don't touch.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


register_exception_handlers(app)

app.include_router(health_router)
app.include_router(api_router)


@app.get("/")
async def root():
    return {"name": settings.app_name, "version": "0.1.0", "docs": "/docs"}
