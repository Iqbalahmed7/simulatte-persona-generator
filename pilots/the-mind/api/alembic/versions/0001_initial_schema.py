"""Initial schema — Auth.js tables + allowances + events

Revision ID: 0001
Revises:
Create Date: 2026-04-26

IMPORTANT: @auth/pg-adapter expects EXACT camelCase column names with quoted
identifiers (e.g. "userId", "providerAccountId", "sessionToken",
"emailVerified"). Do NOT change to snake_case — the adapter's SQL queries
hard-code these names.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw SQL so we get the exact quoted camelCase identifiers the
    # @auth/pg-adapter expects. SQLAlchemy lowercases unquoted identifiers,
    # which breaks the adapter.
    op.execute(
        """
        CREATE TABLE users (
            id TEXT NOT NULL PRIMARY KEY DEFAULT gen_random_uuid()::text,
            name TEXT,
            email TEXT UNIQUE,
            "emailVerified" TIMESTAMPTZ,
            image TEXT
        );
        """
    )
    op.execute('CREATE INDEX ix_users_email ON users (email);')

    op.execute(
        """
        CREATE TABLE accounts (
            id TEXT NOT NULL PRIMARY KEY DEFAULT gen_random_uuid()::text,
            "userId" TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            provider TEXT NOT NULL,
            "providerAccountId" TEXT NOT NULL,
            refresh_token TEXT,
            access_token TEXT,
            expires_at BIGINT,
            token_type TEXT,
            scope TEXT,
            id_token TEXT,
            session_state TEXT,
            UNIQUE (provider, "providerAccountId")
        );
        """
    )
    op.execute('CREATE INDEX "ix_accounts_userId" ON accounts ("userId");')

    op.execute(
        """
        CREATE TABLE sessions (
            id TEXT NOT NULL PRIMARY KEY DEFAULT gen_random_uuid()::text,
            "sessionToken" TEXT NOT NULL UNIQUE,
            "userId" TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute('CREATE INDEX "ix_sessions_userId" ON sessions ("userId");')
    op.execute('CREATE INDEX "ix_sessions_sessionToken" ON sessions ("sessionToken");')

    op.execute(
        """
        CREATE TABLE verification_token (
            identifier TEXT NOT NULL,
            expires TIMESTAMPTZ NOT NULL,
            token TEXT NOT NULL,
            PRIMARY KEY (identifier, token)
        );
        """
    )
    op.execute('CREATE INDEX ix_verification_token_token ON verification_token (token);')

    # ── allowances (our table — snake_case is fine) ───────────────────────
    op.execute(
        """
        CREATE TABLE allowances (
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            week_starting DATE NOT NULL,
            personas_used INTEGER NOT NULL DEFAULT 0,
            probes_used INTEGER NOT NULL DEFAULT 0,
            chats_used INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, week_starting)
        );
        """
    )
    op.execute('CREATE INDEX ix_allowances_user_id ON allowances (user_id);')
    op.execute('CREATE INDEX ix_allowances_week_starting ON allowances (week_starting);')

    # ── events (our table — snake_case is fine) ───────────────────────────
    op.execute(
        """
        CREATE TYPE eventtype AS ENUM (
            'persona_generated', 'probe_run', 'chat_message', 'persona_shared'
        );
        """
    )
    op.execute(
        """
        CREATE TABLE events (
            id TEXT NOT NULL PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type eventtype NOT NULL,
            ref_id TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute('CREATE INDEX ix_events_user_id ON events (user_id);')
    op.execute('CREATE INDEX ix_events_created_at ON events (created_at);')


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS events;")
    op.execute("DROP TYPE IF EXISTS eventtype;")
    op.execute("DROP TABLE IF EXISTS allowances;")
    op.execute("DROP TABLE IF EXISTS verification_token;")
    op.execute("DROP TABLE IF EXISTS sessions;")
    op.execute("DROP TABLE IF EXISTS accounts;")
    op.execute("DROP TABLE IF EXISTS users;")
