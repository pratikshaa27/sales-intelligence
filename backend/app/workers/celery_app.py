from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sales_intelligence",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.product_tasks", "app.workers.research_tasks", "app.workers.import_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=30,
)


@celery_app.task(name="worker.ping")
def ping() -> str:
    return "pong"
