"""SQLAlchemy ORM models for Persona Generator standalone service."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Cohort(Base):
    __tablename__ = "cohorts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    brief_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    gate_warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    total_cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    generator_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_module: Mapped[str | None] = mapped_column(String(128), nullable=True)

    personas: Mapped[list["Persona"]] = relationship(
        "Persona",
        back_populates="cohort",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_cohorts_status_created_at", "status", "created_at"),
    )


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cohort_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohorts.id", ondelete="CASCADE"),
        nullable=False,
    )
    persona_index: Mapped[int] = mapped_column(Integer, nullable=False)
    dossier_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    life_stories: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    picture_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    cohort: Mapped["Cohort"] = relationship("Cohort", back_populates="personas")

    __table_args__ = (
        Index("ix_personas_cohort_index", "cohort_id", "persona_index"),
    )


class CalibrationJob(Base):
    __tablename__ = "calibration_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohorts.id", ondelete="SET NULL"),
        nullable=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    callback_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    callback_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_calibration_jobs_status_created_at", "status", "created_at"),
    )


class CostEvent(Base):
    __tablename__ = "cost_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    tenant_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_usd: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    event_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
