import logging

import redis.asyncio as redis
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import check_database_health

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness probe: process is up. Must not depend on downstream services."""
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    """Readiness probe: are dependencies (DB, Redis) reachable."""
    db_ok = await check_database_health()

    redis_ok = False
    try:
        client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        redis_ok = True
    except Exception:
        logger.warning("redis_health_check_failed")

    checks = {"database": db_ok, "redis": redis_ok}
    status_code = 200 if all(checks.values()) else 503
    body = {"status": "ok" if status_code == 200 else "degraded", "checks": checks}
    return JSONResponse(status_code=status_code, content=body)
