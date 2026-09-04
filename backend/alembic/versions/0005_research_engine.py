"""research engine: research_jobs, research_evidence

Revision ID: 0005_research_engine
Revises: 0004_companies_contacts
Create Date: 2026-09-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_research_engine"
down_revision: Union[str, None] = "0004_companies_contacts"
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
        "research_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "job_type",
            sa.Enum("company_discovery", "company_research", name="job_type", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "completed",
                "failed",
                "cancelled",
                name="job_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("input_parameters", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("progress_percentage", sa.Integer, nullable=False, server_default="0"),
        sa.Column("current_step", sa.String(255), nullable=False, server_default=""),
        sa.Column("logs", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("result_summary", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text, nullable=False, server_default=""),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_research_jobs_organization_id", "research_jobs", ["organization_id"])
    op.create_index("ix_research_jobs_job_type", "research_jobs", ["job_type"])
    op.create_index("ix_research_jobs_status", "research_jobs", ["status"])

    op.create_table(
        "research_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "research_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "category",
            sa.Enum(
                "overview",
                "technology_stack",
                "hiring_signal",
                "expansion_signal",
                "digital_transformation_signal",
                "security_signal",
                "business_challenge",
                "other",
                name="evidence_category",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("fact_text", sa.Text, nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=False),
        sa.Column("source_title", sa.String(500), nullable=False, server_default=""),
        sa.Column("source_type", SOURCE_TYPE_ENUM, nullable=False, server_default="website"),
        sa.Column("source_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_ai_generated", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_research_evidence_company_id", "research_evidence", ["company_id"])


def downgrade() -> None:
    op.drop_table("research_evidence")
    op.drop_table("research_jobs")
