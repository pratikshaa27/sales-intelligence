import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.product import (
    Product,
    ProductCategory,
    ProductDocument,
    ProductEmbedding,
    ProductStatus,
)


class ProductCategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> Sequence[ProductCategory]:
        result = await self.db.execute(select(ProductCategory).order_by(ProductCategory.name))
        return result.scalars().all()

    async def get_by_id(self, category_id: uuid.UUID) -> ProductCategory | None:
        return await self.db.get(ProductCategory, category_id)

    async def get_by_name(self, name: str) -> ProductCategory | None:
        result = await self.db.execute(select(ProductCategory).where(ProductCategory.name == name))
        return result.scalar_one_or_none()

    async def create(self, *, name: str, description: str = "") -> ProductCategory:
        category = ProductCategory(name=name, description=description)
        self.db.add(category)
        await self.db.flush()
        return category


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, *, organization_id: uuid.UUID, product_id: uuid.UUID
    ) -> Product | None:
        result = await self.db.execute(
            select(Product)
            .options(joinedload(Product.category), joinedload(Product.embedding))
            .where(Product.id == product_id, Product.organization_id == organization_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_by_code(self, *, organization_id: uuid.UUID, code: str) -> Product | None:
        result = await self.db.execute(
            select(Product).where(Product.organization_id == organization_id, Product.code == code)
        )
        return result.scalar_one_or_none()

    async def create(self, **fields) -> Product:
        product = Product(**fields)
        self.db.add(product)
        await self.db.flush()
        return product

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
    ) -> tuple[Sequence[Product], int]:
        conditions = [Product.organization_id == organization_id]
        if search:
            like = f"%{search}%"
            conditions.append(
                or_(
                    Product.name.ilike(like),
                    Product.code.ilike(like),
                    Product.short_description.ilike(like),
                )
            )
        if category_id:
            conditions.append(Product.category_id == category_id)
        if industry:
            conditions.append(Product.target_industries.contains([industry]))
        if status:
            conditions.append(Product.status == status)

        base_query = select(Product).options(joinedload(Product.category)).where(*conditions)
        count_query = select(func.count()).select_from(Product).where(*conditions)

        total = (await self.db.execute(count_query)).scalar_one()
        result = await self.db.execute(
            base_query.order_by(Product.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.unique().scalars().all(), total

    async def delete(self, product: Product) -> None:
        await self.db.delete(product)

    async def list_active(self, *, organization_id: uuid.UUID) -> Sequence[Product]:
        result = await self.db.execute(
            select(Product).where(
                Product.organization_id == organization_id,
                Product.status == ProductStatus.ACTIVE,
            )
        )
        return result.scalars().all()


class ProductDocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **fields) -> ProductDocument:
        document = ProductDocument(**fields)
        self.db.add(document)
        await self.db.flush()
        return document

    async def list_for_product(self, product_id: uuid.UUID) -> Sequence[ProductDocument]:
        result = await self.db.execute(
            select(ProductDocument)
            .where(ProductDocument.product_id == product_id)
            .order_by(ProductDocument.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_id(self, document_id: uuid.UUID) -> ProductDocument | None:
        return await self.db.get(ProductDocument, document_id)


class ProductEmbeddingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_product_id(self, product_id: uuid.UUID) -> ProductEmbedding | None:
        result = await self.db.execute(
            select(ProductEmbedding).where(ProductEmbedding.product_id == product_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        product_id: uuid.UUID,
        organization_id: uuid.UUID,
        embedding: list[float],
        embedding_model: str,
        source_text: str,
        generated_at,
    ) -> ProductEmbedding:
        existing = await self.get_by_product_id(product_id)
        if existing:
            existing.embedding = embedding
            existing.embedding_model = embedding_model
            existing.source_text = source_text
            existing.generated_at = generated_at
            await self.db.flush()
            return existing

        record = ProductEmbedding(
            product_id=product_id,
            organization_id=organization_id,
            embedding=embedding,
            embedding_model=embedding_model,
            source_text=source_text,
            generated_at=generated_at,
        )
        self.db.add(record)
        await self.db.flush()
        return record
