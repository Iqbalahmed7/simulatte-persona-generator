"""SQLAlchemy async + sync session helpers.

Provides:
    - Base (declarative base)
    - init_engine(url) — initialise engine + sessionmaker
    - get_session() — async session dependency for FastAPI
    - get_session_sync() — sync session for the worker process
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import AsyncIterator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session


class Base(DeclarativeBase):
    pass


_async_engine = None
_async_sessionmaker: async_sessionmaker[AsyncSession] | None = None
_sync_engine = None
_sync_sessionmaker: sessionmaker[Session] | None = None


def _normalise_async_url(url: str) -> str:
    """Convert postgres:// URLs to postgresql+asyncpg:// for asyncpg driver."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


def _normalise_sync_url(url: str) -> str:
    """Convert async URL to sync (psycopg2 / pg8000-compatible)."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://"):]
    return url


def init_engine(database_url: str | None = None) -> None:
    """Initialise both async and sync engines."""
    global _async_engine, _async_sessionmaker, _sync_engine, _sync_sessionmaker

    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL not set. Required for Persona Generator standalone service."
        )

    async_url = _normalise_async_url(url)
    sync_url = _normalise_sync_url(url)

    _async_engine = create_async_engine(async_url, pool_pre_ping=True, future=True)
    _async_sessionmaker = async_sessionmaker(
        _async_engine, class_=AsyncSession, expire_on_commit=False
    )

    _sync_engine = create_engine(sync_url, pool_pre_ping=True, future=True)
    _sync_sessionmaker = sessionmaker(_sync_engine, expire_on_commit=False)


def _ensure_initialised() -> None:
    if _async_sessionmaker is None or _sync_sessionmaker is None:
        init_engine()


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — yields an AsyncSession."""
    _ensure_initialised()
    assert _async_sessionmaker is not None
    async with _async_sessionmaker() as session:
        try:
            yield session
        finally:
            await session.close()


@contextmanager
def get_session_sync() -> Iterator[Session]:
    """Sync session for worker / scripts."""
    _ensure_initialised()
    assert _sync_sessionmaker is not None
    session = _sync_sessionmaker()
    try:
        yield session
    finally:
        session.close()
