"""pilots/the-mind/api/db.py — SQLAlchemy 2.0 async models + engine factory.

Six tables:
  Auth.js standard (frontend reads/writes):
    users, accounts, sessions, verification_tokens

  Mind sandbox (backend reads/writes):
    allowances, events

Usage:
    from db import get_db, User, Allowance, Event
    async with get_db() as session:
        user = await session.get(User, user_id)
"""
from __future__ import annotations

import enum
import os
import uuid
from datetime import date, datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship

# ── Engine ────────────────────────────────────────────────────────────────

def _make_engine():
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    # SQLAlchemy async requires postgresql+asyncpg:// driver prefix
    if raw_url.startswith("postgresql://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return create_async_engine(
        raw_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )


_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with get_session_factory()() as session:
        yield session


# ── Base ──────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Auth.js standard tables ───────────────────────────────────────────────

class User(Base):
    """Auth.js users table. Auth.js creates/updates this; FastAPI reads it.

    NOTE: column names use camelCase quoted identifiers (Auth.js convention).
    SQLAlchemy attribute names stay snake_case for Pythonic access; the
    Column("camelCase", ...) form maps them to the actual DB columns.
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    image = Column(Text, nullable=True)
    email_verified = Column("emailVerified", DateTime(timezone=True), nullable=True)

    allowance = relationship("Allowance", back_populates="user", uselist=False)
    events = relationship("Event", back_populates="user")

    __table_args__ = (
        Index("ix_users_email", "email"),
    )


class Account(Base):
    """Auth.js accounts table (OAuth provider tokens)."""
    __tablename__ = "accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    provider_account_id = Column("providerAccountId", String, nullable=False)
    refresh_token = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    expires_at = Column(BigInteger, nullable=True)
    token_type = Column(String, nullable=True)
    scope = Column(String, nullable=True)
    id_token = Column(Text, nullable=True)
    session_state = Column(String, nullable=True)


class Session(Base):
    """Auth.js sessions table."""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_token = Column("sessionToken", String, unique=True, nullable=False)
    user_id = Column("userId", String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires = Column(DateTime(timezone=True), nullable=False)


class VerificationToken(Base):
    """Auth.js verification_tokens table (magic link tokens)."""
    __tablename__ = "verification_token"

    identifier = Column(String, primary_key=True, nullable=False)
    token = Column(String, primary_key=True, nullable=False)
    expires = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_verification_tokens_token", "token"),
    )


# ── Mind sandbox tables ───────────────────────────────────────────────────

class Allowance(Base):
    """Per-user, per-ISO-week allowance counters.

    Primary key is (user_id, week_starting) — one row per user per week.
    Backend upserts this row on every gated action.
    """
    __tablename__ = "allowances"

    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    week_starting = Column(Date, primary_key=True, nullable=False)

    personas_used = Column(Integer, nullable=False, default=0, server_default="0")
    probes_used = Column(Integer, nullable=False, default=0, server_default="0")
    chats_used = Column(Integer, nullable=False, default=0, server_default="0")

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="allowance")

    __table_args__ = (
        Index("ix_allowances_user_id", "user_id"),
        Index("ix_allowances_week_starting", "week_starting"),
    )


class EventType(str, enum.Enum):
    persona_generated = "persona_generated"
    probe_run = "probe_run"
    chat_message = "chat_message"
    persona_shared = "persona_shared"


class Event(Base):
    """Audit log of every billable action a user takes."""
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type = Column(SAEnum(EventType), nullable=False)
    ref_id = Column(String, nullable=True)   # persona_id, probe_id, etc.
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="events")

    __table_args__ = (
        Index("ix_events_user_id", "user_id"),
        Index("ix_events_created_at", "created_at"),
    )


# ── Allowance limits (hard-coded, can be per-user later) ─────────────────

LIMITS = {
    "persona": 1,
    "probe": 3,
    "chat": 5,
}
