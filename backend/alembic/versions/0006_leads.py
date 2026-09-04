"""lead intelligence: leads, lead_scores, sales_briefs, lead_notes, lead_activities

Revision ID: 0006_leads
Revises: 0005_research_engine
Create Date: 2026-09-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_leads"
down_revision: Union[str, None] = "0005_research_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leads",
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
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source", sa.String(255), nullable=False, server_default="manual"),
        sa.Column(
            "status",
            sa.Enum(
                "new",
                "researching",
                "qualified",
                "assigned",
                "contacted",
                "meeting_scheduled",
                "proposal_sent",
                "negotiation",
                "won",
                "lost",
                "disqualified",
                "archived",
                name="lead_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "priority",
            sa.Enum("low", "medium", "high", "critical", name="lead_priority", native_enum=False),
            nullable=False,
            server_default="low",
        ),
        sa.Column("total_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fit_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("need_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("authority_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("timing_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("data_confidence_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("research_summary", sa.Text, nullable=False, server_default=""),
        sa.Column("next_action", sa.String(500), nullable=False, server_default=""),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
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
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_leads_organization_id", "leads", ["organization_id"])
    op.create_index("ix_leads_company_id", "leads", ["company_id"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_priority", "leads", ["priority"])

    op.create_table(
        "lead_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lead_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("total_score", sa.Integer, nullable=False),
        sa.Column("fit_score", sa.Integer, nullable=False),
        sa.Column("need_score", sa.Integer, nullable=False),
        sa.Column("authority_score", sa.Integer, nullable=False),
        sa.Column("timing_score", sa.Integer, nullable=False),
        sa.Column("confidence_score", sa.Integer, nullable=False),
        sa.Column("reasons", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("missing_information", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_lead_scores_lead_id", "lead_scores", ["lead_id"])

    op.create_table(
        "sales_briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lead_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_overview", sa.Text, nullable=False, server_default=""),
        sa.Column("why_relevant", sa.Text, nullable=False, server_default=""),
        sa.Column("matched_product_summary", sa.Text, nullable=False, server_default=""),
        sa.Column("possible_business_problem", sa.Text, nullable=False, server_default=""),
        sa.Column("evidence_summary", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("relevant_decision_maker", sa.String(500), nullable=False, server_default=""),
        sa.Column("suggested_opener", sa.Text, nullable=False, server_default=""),
        sa.Column("discovery_questions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("recommended_next_action", sa.Text, nullable=False, server_default=""),
        sa.Column("missing_information", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("disclaimer", sa.Text, nullable=False, server_default=""),
        sa.Column("ai_provider", sa.String(64), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_sales_briefs_lead_id", "sales_briefs", ["lead_id"])

    op.create_table(
        "lead_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lead_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_lead_notes_lead_id", "lead_notes", ["lead_id"])

    op.create_table(
        "lead_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lead_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
            "activity_type",
            sa.Enum(
                "created",
                "status_changed",
                "assigned",
                "note_added",
                "score_recalculated",
                "brief_generated",
                "research_rerun",
                "other",
                name="activity_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("event_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_lead_activities_lead_id", "lead_activities", ["lead_id"])


def downgrade() -> None:
    op.drop_table("lead_activities")
    op.drop_table("lead_notes")
    op.drop_table("sales_briefs")
    op.drop_table("lead_scores")
    op.drop_table("leads")
