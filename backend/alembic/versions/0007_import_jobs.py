"""background CSV import tracking: import_jobs

Revision ID: 0007_import_jobs
Revises: 0006_leads
Create Date: 2026-09-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_import_jobs"
down_revision: Union[str, None] = "0006_leads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "import_jobs",
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
            "entity_type",
            sa.Enum(
                "company",
                "contact",
                "product",
                "lead",
                name="import_entity_type",
                native_enum=False,
            ),
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
                name="import_job_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("progress_percentage", sa.Integer, nullable=False, server_default="0"),
        sa.Column("current_step", sa.String(255), nullable=False, server_default=""),
        sa.Column("logs", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("total_rows", sa.Integer, nullable=False, server_default="0"),
        sa.Column("processed_rows", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("row_errors", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text, nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_import_jobs_organization_id", "import_jobs", ["organization_id"])
    op.create_index("ix_import_jobs_entity_type", "import_jobs", ["entity_type"])
    op.create_index("ix_import_jobs_status", "import_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("import_jobs")
