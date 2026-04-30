"""the_operator/migrations.py — idempotent SQL migrations for Operator tables.

Called at startup inside lifespan() when OPERATOR_ENABLED=true.
Mirrors the _ensure_probes_table style from main.py exactly.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("the_operator")


async def _ensure_operator_tables() -> None:
    """Create all Operator tables and indexes — idempotent, safe to re-run."""
    try:
        from db import get_engine              # noqa: PLC0415
        from sqlalchemy import text as _sql   # noqa: PLC0415

        engine = get_engine()
        async with engine.begin() as conn:

            # ── twins ────────────────────────────────────────────────────
            await conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS twins (
                    id              VARCHAR PRIMARY KEY,
                    user_id         VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    full_name       VARCHAR NOT NULL,
                    company         VARCHAR,
                    title           VARCHAR,
                    name_slug       VARCHAR NOT NULL,
                    mode            VARCHAR NOT NULL DEFAULT 'standard',
                    confidence      VARCHAR NOT NULL DEFAULT 'medium',
                    sources_count   INTEGER NOT NULL DEFAULT 0,
                    gaps            TEXT,
                    recon_notes     TEXT,
                    profile         TEXT NOT NULL DEFAULT '{}',
                    enrichment      TEXT,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    last_probed_at  TIMESTAMP WITH TIME ZONE,
                    last_refreshed_at TIMESTAMP WITH TIME ZONE
                )
            """))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_twins_user_id ON twins (user_id)"
            ))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_twins_name_slug ON twins (name_slug)"
            ))
            await conn.execute(_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_twins_user_slug ON twins (user_id, name_slug)"
            ))

            # ── twin_probe_sessions ───────────────────────────────────────
            await conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS twin_probe_sessions (
                    id              VARCHAR PRIMARY KEY,
                    twin_id         VARCHAR NOT NULL REFERENCES twins(id) ON DELETE CASCADE,
                    user_id         VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    started_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    last_message_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    ended_at        TIMESTAMP WITH TIME ZONE,
                    message_count   INTEGER NOT NULL DEFAULT 0
                )
            """))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_tps_twin_id ON twin_probe_sessions (twin_id)"
            ))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_tps_user_id ON twin_probe_sessions (user_id)"
            ))

            # ── twin_probe_messages ───────────────────────────────────────
            await conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS twin_probe_messages (
                    id         VARCHAR PRIMARY KEY,
                    session_id VARCHAR NOT NULL REFERENCES twin_probe_sessions(id) ON DELETE CASCADE,
                    role       VARCHAR NOT NULL,
                    content    TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    flagged    BOOLEAN NOT NULL DEFAULT false
                )
            """))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_tpm_session_id ON twin_probe_messages (session_id)"
            ))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_tpm_created_at ON twin_probe_messages (created_at)"
            ))

            # ── twin_frame_scores ─────────────────────────────────────────
            await conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS twin_frame_scores (
                    id                VARCHAR PRIMARY KEY,
                    twin_id           VARCHAR NOT NULL REFERENCES twins(id) ON DELETE CASCADE,
                    user_id           VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    message_input     TEXT NOT NULL,
                    score_payload     TEXT NOT NULL,
                    overall_score     REAL,
                    reply_probability VARCHAR,
                    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                )
            """))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_tfs_twin_id ON twin_frame_scores (twin_id)"
            ))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_tfs_user_id ON twin_frame_scores (user_id)"
            ))

            # ── operator_allowances ───────────────────────────────────────
            await conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS operator_allowances (
                    user_id        VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    week_starting  DATE NOT NULL,
                    twins_built    INTEGER NOT NULL DEFAULT 0,
                    twin_refreshes INTEGER NOT NULL DEFAULT 0,
                    probe_messages INTEGER NOT NULL DEFAULT 0,
                    frame_scores   INTEGER NOT NULL DEFAULT 0,
                    updated_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    PRIMARY KEY (user_id, week_starting)
                )
            """))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_op_allowances_user_id ON operator_allowances (user_id)"
            ))

        logger.info("[operator] all tables ensured")

    except Exception as exc:  # pragma: no cover
        logger.warning("[operator] migration skipped: %s", exc)
