"""initial schema for standalone PG service

Revision ID: 20260507_0001
Revises:
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260507_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cohorts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("brief_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("summary", postgresql.JSONB, nullable=True),
        sa.Column("gate_warnings", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("total_cost_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column("generator_version", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_module", sa.String(128), nullable=True),
    )
    op.create_index("ix_cohorts_tenant_id", "cohorts", ["tenant_id"])
    op.create_index("ix_cohorts_status_created_at", "cohorts", ["status", "created_at"])

    op.create_table(
        "personas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cohort_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cohorts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("persona_index", sa.Integer, nullable=False),
        sa.Column("dossier_snapshot", postgresql.JSONB, nullable=False),
        sa.Column("life_stories", postgresql.JSONB, nullable=True),
        sa.Column("content_hash", sa.String(128), nullable=True),
        sa.Column("picture_url", sa.Text, nullable=True),
        sa.Column("display_bio", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_personas_cohort_index", "personas", ["cohort_id", "persona_index"])

    op.create_table(
        "calibration_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cohort_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cohorts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("callback_url", sa.Text, nullable=True),
        sa.Column("callback_secret", sa.Text, nullable=True),
    )
    op.create_index("ix_calibration_jobs_tenant_id", "calibration_jobs", ["tenant_id"])
    op.create_index(
        "ix_calibration_jobs_status_created_at",
        "calibration_jobs",
        ["status", "created_at"],
    )

    op.create_table(
        "cost_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cohort_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", sa.String(128), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("amount_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cost_events_cohort_id", "cost_events", ["cohort_id"])
    op.create_index("ix_cost_events_tenant_id", "cost_events", ["tenant_id"])
    op.create_index("ix_cost_events_created_at", "cost_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("cost_events")
    op.drop_table("calibration_jobs")
    op.drop_table("personas")
    op.drop_table("cohorts")
