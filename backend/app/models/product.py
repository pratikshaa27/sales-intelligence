import uuid
from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin

EMBEDDING_DIMENSIONS = 1536


class ProductStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class EmbeddingStatus(StrEnum):
    NONE = "none"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProductCategory(UUIDPKMixin, TimestampMixin, Base):
    """Global, platform-wide taxonomy (spec §3: Super Admin manages product categories) —
    not tenant-scoped, shared across every organization."""

    __tablename__ = "product_categories"

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Product(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "products"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    short_description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    detailed_description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    target_industries: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    target_company_size: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    target_geographic_regions: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    business_problems: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    key_features: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    benefits: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    pricing_model: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    minimum_contract_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    required_technical_capabilities: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    supported_integrations: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    ideal_customer_profile: Mapped[str] = mapped_column(Text, default="", nullable=False)
    common_use_cases: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    competitor_alternatives: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status", native_enum=False),
        default=ProductStatus.DRAFT,
        nullable=False,
        index=True,
    )
    embedding_status: Mapped[EmbeddingStatus] = mapped_column(
        Enum(EmbeddingStatus, name="embedding_status", native_enum=False),
        default=EmbeddingStatus.NONE,
        nullable=False,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    category: Mapped["ProductCategory | None"] = relationship()
    documents: Mapped[list["ProductDocument"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    embedding: Mapped["ProductEmbedding | None"] = relationship(
        back_populates="product", cascade="all, delete-orphan", uselist=False
    )


class ProductDocument(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "product_documents"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    product: Mapped["Product"] = relationship(back_populates="documents")


class ProductEmbedding(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "product_embeddings"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="embedding")
