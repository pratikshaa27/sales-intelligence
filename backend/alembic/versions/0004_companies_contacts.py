"""company and contact management: companies, company_sources, contacts, contact_sources

Revision ID: 0004_companies_contacts
Revises: 0003_products
Create Date: 2026-09-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_companies_contacts"
down_revision: Union[str, None] = "0003_products"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SOURCE_TYPE_ENUM = sa.Enum(
    "website",
    "directory",
    "news",
    "job_posting",
    "social_profile",
    "other",
    name="source_type",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("website", sa.String(500), nullable=False, server_default=""),
        sa.Column("industry", sa.String(255), nullable=False, server_default=""),
        sa.Column("locations", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("company_size", sa.String(64), nullable=False, server_default=""),
        sa.Column("revenue_range", sa.String(64), nullable=False, server_default=""),
        sa.Column("business_description", sa.Text, nullable=False, server_default=""),
        sa.Column("technology_stack", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("business_challenges", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("public_signals", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("confidence_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "research_status",
            sa.Enum(
                "not_researched",
                "researching",
                "researched",
                "failed",
                name="research_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="not_researched",
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
        sa.UniqueConstraint("organization_id", "domain", name="uq_companies_org_domain"),
    )
    op.create_index("ix_companies_organization_id", "companies", ["organization_id"])

    op.create_table(
        "company_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("source_type", SOURCE_TYPE_ENUM, nullable=False, server_default="other"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "added_by",
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
    op.create_index("ix_company_sources_company_id", "company_sources", ["company_id"])

    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("job_title", sa.String(255), nullable=False, server_default=""),
        sa.Column("department", sa.String(255), nullable=False, server_default=""),
        sa.Column("seniority", sa.String(64), nullable=False, server_default=""),
        sa.Column("role_relevance", sa.String(500), nullable=False, server_default=""),
        sa.Column("profile_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("business_email", sa.String(320), nullable=False, server_default=""),
        sa.Column("business_phone", sa.String(64), nullable=False, server_default=""),
        sa.Column(
            "verification_status",
            sa.Enum(
                "unverified", "verified", "disputed", name="verification_status", native_enum=False
            ),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column("confidence_score", sa.Integer, nullable=False, server_default="0"),
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
    )
    op.create_index("ix_contacts_organization_id", "contacts", ["organization_id"])
    op.create_index("ix_contacts_company_id", "contacts", ["company_id"])

    op.create_table(
        "contact_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("source_type", SOURCE_TYPE_ENUM, nullable=False, server_default="other"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "added_by",
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
    op.create_index("ix_contact_sources_contact_id", "contact_sources", ["contact_id"])


def downgrade() -> None:
    op.drop_table("contact_sources")
    op.drop_table("contacts")
    op.drop_table("company_sources")
    op.drop_table("companies")
