import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.provider import EmbeddingProviderError, get_embedding_provider
from app.core.config import get_settings
from app.models.product import EmbeddingStatus, Product
from app.repositories.product_repository import ProductEmbeddingRepository
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def compose_embedding_text(product: Product) -> str:
    parts = [
        product.name,
        product.short_description,
        product.detailed_description,
        "Target industries: " + ", ".join(product.target_industries),
        "Business problems solved: " + ", ".join(product.business_problems),
        "Key features: " + ", ".join(product.key_features),
        "Benefits: " + ", ".join(product.benefits),
        "Ideal customer profile: " + product.ideal_customer_profile,
        "Common use cases: " + ", ".join(product.common_use_cases),
    ]
    return "\n".join(p for p in parts if p and p.strip())


async def _generate_embedding_async(product_id: str) -> None:
    # A dedicated engine per task invocation — NOT the shared app.core.database engine.
    # Celery calls this via a fresh asyncio.run() each time, which means a fresh event loop
    # each time; asyncpg connections (and SQLAlchemy's pool holding them) cannot be reused
    # across different event loops, so sharing a module-level pool here would intermittently
    # hand a task a connection born in a previous loop and fail with "attached to a different
    # loop". A short-lived engine, disposed at the end of this call, avoids that entirely.
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            product = await db.get(Product, uuid.UUID(product_id))
            if product is None:
                logger.warning("product_not_found_for_embedding", extra={"product_id": product_id})
                return

            product.embedding_status = EmbeddingStatus.PROCESSING
            await db.commit()

            try:
                provider = get_embedding_provider()
                text = compose_embedding_text(product)
                vector = await provider.embed(text)

                repo = ProductEmbeddingRepository(db)
                await repo.upsert(
                    product_id=product.id,
                    organization_id=product.organization_id,
                    embedding=vector,
                    embedding_model=getattr(provider, "model", provider.name),
                    source_text=text,
                    generated_at=datetime.now(UTC),
                )
                product.embedding_status = EmbeddingStatus.COMPLETED
                await db.commit()
            except EmbeddingProviderError:
                product.embedding_status = EmbeddingStatus.FAILED
                await db.commit()
                raise
    finally:
        await engine.dispose()


@celery_app.task(
    name="products.generate_embedding", bind=True, max_retries=3, default_retry_delay=30
)
def generate_product_embedding(self, product_id: str) -> str:
    try:
        asyncio.run(_generate_embedding_async(product_id))
        return "completed"
    except EmbeddingProviderError as exc:
        logger.warning("product_embedding_task_failed", extra={"product_id": product_id})
        raise self.retry(exc=exc) from exc
