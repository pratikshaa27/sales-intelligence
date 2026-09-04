"""product management: categories, products, documents, embeddings

Revision ID: 0003_products
Revises: 0002_seed_rbac
Create Date: 2026-09-03

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from app.core.seed_data import DEFAULT_PRODUCT_CATEGORIES

revision: str = "0003_products"
down_revision: Union[str, None] = "0002_seed_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMENSIONS = 1536

product_categories_table = sa.table(
    "product_categories",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
)


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_product_categories_name", "product_categories", ["name"], unique=True)

    op.bulk_insert(
        product_categories_table,
        [
            {"id": uuid.uuid4(), "name": name, "description": ""}
            for name in DEFAULT_PRODUCT_CATEGORIES
        ],
    )

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("short_description", sa.String(500), nullable=False, server_default=""),
        sa.Column("detailed_description", sa.Text, nullable=False, server_default=""),
        sa.Column("target_industries", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("target_company_size", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "target_geographic_regions", postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column("business_problems", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("key_features", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("benefits", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("pricing_model", sa.String(255), nullable=False, server_default=""),
        sa.Column("minimum_contract_value", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "required_technical_capabilities", postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column("supported_integrations", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("ideal_customer_profile", sa.Text, nullable=False, server_default=""),
        sa.Column("common_use_cases", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("competitor_alternatives", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "status",
            sa.Enum("draft", "active", "archived", name="product_status", native_enum=False),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "embedding_status",
            sa.Enum(
                "none",
                "queued",
                "processing",
                "completed",
                "failed",
                name="embedding_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="none",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("organization_id", "code", name="uq_products_org_code"),
    )
    op.create_index("ix_products_organization_id", "products", ["organization_id"])
    op.create_index("ix_products_status", "products", ["status"])

    op.create_table(
        "product_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_product_documents_product_id", "product_documents", ["product_id"])

    op.create_table(
        "product_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column("embedding_model", sa.String(128), nullable=False),
        sa.Column("source_text", sa.Text, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_product_embeddings_product_id", "product_embeddings", ["product_id"], unique=True
    )
    op.execute(
        "CREATE INDEX ix_product_embeddings_vector ON product_embeddings "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_table("product_embeddings")
    op.drop_table("product_documents")
    op.drop_table("products")
    op.drop_table("product_categories")
