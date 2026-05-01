"""the_operator/models.py — SQLAlchemy ORM models for the Operator module.

Uses the same Base from db.py so all tables live in the same metadata.
FKs point to users(id) only — never to other PG tables.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint, Date,
)

from db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Twin(Base):
    __tablename__ = "twins"

    id             = Column(String, primary_key=True)
    user_id        = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # subject
    full_name      = Column(String, nullable=False)
    company        = Column(String, nullable=True)
    title          = Column(String, nullable=True)
    name_slug      = Column(String, nullable=False)          # "vilma-livas-banza"

    # build metadata
    mode           = Column(String, nullable=False, default="standard")   # standard | enriched | lite
    confidence     = Column(String, nullable=False, default="medium")     # high | medium | low
    sources_count  = Column(Integer, nullable=False, default=0)
    gaps           = Column(Text, nullable=True)

    # content
    recon_notes    = Column(Text, nullable=True)             # raw recon intermediate JSON
    profile        = Column(Text, nullable=False)            # synthesised Twin profile JSON
    enrichment     = Column(Text, nullable=True)             # user-pasted enrichment signals
    portrait_url   = Column(Text, nullable=True)             # fal.ai Flux portrait URL

    # timestamps
    created_at        = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at        = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    last_probed_at    = Column(DateTime(timezone=True), nullable=True)
    last_refreshed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_twins_user_id", "user_id"),
        Index("ix_twins_name_slug", "name_slug"),
        UniqueConstraint("user_id", "name_slug", name="uq_twins_user_slug"),
    )


class TwinProbeSession(Base):
    __tablename__ = "twin_probe_sessions"

    id              = Column(String, primary_key=True)
    twin_id         = Column(String, ForeignKey("twins.id", ondelete="CASCADE"), nullable=False)
    user_id         = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at      = Column(DateTime(timezone=True), nullable=False, default=_now)
    last_message_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    ended_at        = Column(DateTime(timezone=True), nullable=True)
    message_count   = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_tps_twin_id", "twin_id"),
        Index("ix_tps_user_id", "user_id"),
    )


class TwinProbeMessage(Base):
    """One row per message. role: 'user' | 'twin' | 'operator_note'"""
    __tablename__ = "twin_probe_messages"

    id         = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("twin_probe_sessions.id", ondelete="CASCADE"), nullable=False)
    role       = Column(String, nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    flagged    = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_tpm_session_id", "session_id"),
        Index("ix_tpm_created_at", "created_at"),
    )


class TwinFrameScore(Base):
    __tablename__ = "twin_frame_scores"

    id               = Column(String, primary_key=True)
    twin_id          = Column(String, ForeignKey("twins.id", ondelete="CASCADE"), nullable=False)
    user_id          = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_input    = Column(Text, nullable=False)
    score_payload    = Column(Text, nullable=False)           # full annotated JSON
    overall_score    = Column(Float, nullable=True)
    reply_probability = Column(String, nullable=True)         # high | medium | low
    created_at       = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        Index("ix_tfs_twin_id", "twin_id"),
        Index("ix_tfs_user_id", "user_id"),
    )


class OperatorAllowance(Base):
    """Per-user, per-ISO-week counters. Independent of PG's Allowance table."""
    __tablename__ = "operator_allowances"

    user_id        = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    week_starting  = Column(Date, primary_key=True)
    twins_built    = Column(Integer, nullable=False, default=0, server_default="0")
    twin_refreshes = Column(Integer, nullable=False, default=0, server_default="0")
    probe_messages = Column(Integer, nullable=False, default=0, server_default="0")
    frame_scores   = Column(Integer, nullable=False, default=0, server_default="0")
    updated_at     = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        Index("ix_op_allowances_user_id", "user_id"),
    )
