"""security event log, distinct from audit_logs (spec §11): security_events

Revision ID: 0008_security_events
Revises: 0007_import_jobs
Create Date: 2026-09-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_security_events"
down_revision: Union[str, None] = "0007_import_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "security_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "event_type",
            sa.Enum(
                "login_failed",
                "account_locked",
                "permission_denied",
                "ssrf_blocked",
                "csrf_rejected",
                name="security_event_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "low",
                "medium",
                "high",
                "critical",
                name="security_event_severity",
                native_enum=False,
            ),
            nullable=False,
            server_default="low",
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(512), nullable=False, server_default=""),
        sa.Column("event_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_security_events_organization_id", "security_events", ["organization_id"])
    op.create_index("ix_security_events_user_id", "security_events", ["user_id"])
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_severity", "security_events", ["severity"])


def downgrade() -> None:
    op.drop_table("security_events")
