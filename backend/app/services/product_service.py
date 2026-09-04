import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.core.storage import (
    ALLOWED_CONTENT_TYPES,
    MAX_UPLOAD_SIZE_BYTES,
    UnsupportedFileError,
    build_storage_key,
    get_file_storage,
    sanitize_filename,
    validate_file_signature,
)
from app.models.product import EmbeddingStatus, Product, ProductDocument, ProductStatus
from app.repositories.audit_repository import AuditRepository
from app.repositories.product_repository import (
    ProductCategoryRepository,
    ProductDocumentRepository,
    ProductRepository,
)
from app.schemas.common import PaginationMeta
from app.schemas.product import CreateProductRequest, UpdateProductRequest


class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.products = ProductRepository(db)
        self.categories = ProductCategoryRepository(db)
        self.documents = ProductDocumentRepository(db)
        self.audit = AuditRepository(db)

    async def create(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, body: CreateProductRequest
    ) -> Product:
        existing = await self.products.get_by_code(organization_id=organization_id, code=body.code)
        if existing:
            raise AppError("CONFLICT", f"Product code '{body.code}' is already in use", 409)

        if body.category_id and not await self.categories.get_by_id(body.category_id):
            raise AppError("VALIDATION_ERROR", "Unknown product category", 422)

        product = await self.products.create(
            organization_id=organization_id,
            created_by=user_id,
            updated_by=user_id,
            **body.model_dump(),
        )
        await self.audit.log(
            action="product.created",
            resource_type="product",
            resource_id=str(product.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return await self._reload(organization_id, product.id)

    async def get(self, *, organization_id: uuid.UUID, product_id: uuid.UUID) -> Product:
        product = await self.products.get_by_id(
            organization_id=organization_id, product_id=product_id
        )
        if product is None:
            raise NotFoundError("Product not found")
        return product

    async def update(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        body: UpdateProductRequest,
    ) -> Product:
        product = await self.get(organization_id=organization_id, product_id=product_id)
        updates = body.model_dump(exclude_unset=True)

        if "status" in updates and updates["status"] == ProductStatus.ARCHIVED:
            raise AppError(
                "VALIDATION_ERROR",
                "Use POST /products/{id}/archive to archive a product",
                422,
            )

        if "status" in updates and product.status == ProductStatus.ARCHIVED:
            raise AppError(
                "VALIDATION_ERROR",
                "Use POST /products/{id}/restore to bring an archived product out of archive",
                422,
            )

        if "code" in updates and updates["code"] != product.code:
            existing = await self.products.get_by_code(
                organization_id=organization_id, code=updates["code"]
            )
            if existing:
                raise AppError(
                    "CONFLICT", f"Product code '{updates['code']}' is already in use", 409
                )

        if "category_id" in updates and updates["category_id"] is not None:
            if not await self.categories.get_by_id(updates["category_id"]):
                raise AppError("VALIDATION_ERROR", "Unknown product category", 422)

        for field, value in updates.items():
            setattr(product, field, value)
        product.updated_by = user_id

        await self.audit.log(
            action="product.updated",
            resource_type="product",
            resource_id=str(product.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return await self._reload(organization_id, product.id)

    async def set_status(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        status: ProductStatus,
    ) -> Product:
        product = await self.get(organization_id=organization_id, product_id=product_id)
        product.status = status
        product.updated_by = user_id
        await self.audit.log(
            action=f"product.{status.value}",
            resource_type="product",
            resource_id=str(product.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return await self._reload(organization_id, product.id)

    async def delete(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, product_id: uuid.UUID
    ) -> None:
        product = await self.get(organization_id=organization_id, product_id=product_id)
        if product.status != ProductStatus.DRAFT:
            raise AppError(
                "CONFLICT",
                "Only draft products can be permanently deleted; archive it instead",
                409,
            )
        await self.audit.log(
            action="product.deleted",
            resource_type="product",
            resource_id=str(product.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.products.delete(product)
        await self.db.commit()

    async def list_paginated(
        self,
        *,
        organization_id: uuid.UUID,
        search: str | None,
        category_id: uuid.UUID | None,
        industry: str | None,
        status: ProductStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Product], PaginationMeta]:
        items, total = await self.products.list_paginated(
            organization_id=organization_id,
            search=search,
            category_id=category_id,
            industry=industry,
            status=status,
            page=page,
            page_size=page_size,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return list(items), PaginationMeta(
            page=page, page_size=page_size, total=total, total_pages=total_pages
        )

    async def upload_document(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> ProductDocument:
        product = await self.get(organization_id=organization_id, product_id=product_id)

        if content_type not in ALLOWED_CONTENT_TYPES:
            raise AppError(
                "UNSUPPORTED_FILE_TYPE",
                f"File type '{content_type}' is not allowed for product documents",
                422,
            )
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise AppError("FILE_TOO_LARGE", "File exceeds the 10 MB upload limit", 422)
        if not validate_file_signature(content_type, content):
            raise AppError(
                "UNSUPPORTED_FILE_TYPE",
                "File content does not match its declared type",
                422,
            )

        storage = get_file_storage()
        key = build_storage_key(
            organization_id=organization_id, product_id=product.id, filename=filename
        )
        try:
            await storage.save(key=key, content=content)
        except UnsupportedFileError as exc:
            raise AppError("VALIDATION_ERROR", str(exc), 422) from exc

        document = await self.documents.create(
            product_id=product.id,
            organization_id=organization_id,
            file_name=sanitize_filename(filename),
            content_type=content_type,
            size_bytes=len(content),
            storage_key=key,
            uploaded_by=user_id,
        )
        await self.audit.log(
            action="product.document_uploaded",
            resource_type="product_document",
            resource_id=str(document.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()
        return document

    async def reindex(
        self, *, organization_id: uuid.UUID, user_id: uuid.UUID, product_id: uuid.UUID
    ) -> Product:
        # Imported lazily to avoid importing Celery (and its broker connection setup) into the
        # web process's module-load path unless a reindex is actually requested.
        from app.workers.product_tasks import generate_product_embedding

        product = await self.get(organization_id=organization_id, product_id=product_id)
        product.embedding_status = EmbeddingStatus.QUEUED
        await self.audit.log(
            action="product.reindex_requested",
            resource_type="product",
            resource_id=str(product.id),
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.db.commit()

        try:
            generate_product_embedding.delay(str(product.id))
        except Exception as exc:
            product.embedding_status = EmbeddingStatus.FAILED
            await self.db.commit()
            raise AppError(
                "JOB_QUEUE_UNAVAILABLE", "Could not queue the embedding job; try again shortly", 503
            ) from exc

        # Reload rather than returning `product` directly: the prior commit flushed an UPDATE
        # with an onupdate=func.now() column, which SQLAlchemy marks expired rather than
        # refreshed — reading it later would trigger an implicit synchronous lazy-load that
        # fails under async (see the create/update/set_status methods, which do the same).
        return await self._reload(organization_id, product.id)

    async def _reload(self, organization_id: uuid.UUID, product_id: uuid.UUID) -> Product:
        product = await self.products.get_by_id(
            organization_id=organization_id, product_id=product_id
        )
        assert product is not None
        return product
