"""services/benchmark/storage.py — SQLite persistence for benchmark runs."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Optional

import aiosqlite

from models import BenchmarkReport, RunStatus

DB_PATH = os.environ.get("BENCHMARK_DB_PATH", "benchmark.db")

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS benchmark_runs (
    run_id          TEXT PRIMARY KEY,
    persona_id      TEXT NOT NULL,
    persona_name    TEXT NOT NULL,
    tier            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'queued',
    report_json     TEXT,
    started_at      TEXT,
    completed_at    TEXT,
    error           TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_persona ON benchmark_runs(persona_id);
CREATE INDEX IF NOT EXISTS idx_runs_status  ON benchmark_runs(status);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_CREATE_SQL)
        await db.commit()


async def upsert_run(report: BenchmarkReport) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO benchmark_runs
                (run_id, persona_id, persona_name, tier, status, report_json,
                 started_at, completed_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status       = excluded.status,
                report_json  = excluded.report_json,
                completed_at = excluded.completed_at,
                error        = excluded.error
            """,
            (
                report.run_id,
                report.persona_id,
                report.persona_name,
                report.tier.value,
                report.status.value,
                report.model_dump_json(),
                report.started_at.isoformat() if report.started_at else None,
                report.completed_at.isoformat() if report.completed_at else None,
                report.error,
            ),
        )
        await db.commit()


async def get_run(run_id: str) -> Optional[BenchmarkReport]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT report_json FROM benchmark_runs WHERE run_id = ?", (run_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row or not row[0]:
                return None
            return BenchmarkReport.model_validate_json(row[0])


async def list_runs(persona_id: Optional[str] = None, limit: int = 50) -> List[BenchmarkReport]:
    async with aiosqlite.connect(DB_PATH) as db:
        if persona_id:
            sql = "SELECT report_json FROM benchmark_runs WHERE persona_id = ? ORDER BY started_at DESC LIMIT ?"
            params = (persona_id, limit)
        else:
            sql = "SELECT report_json FROM benchmark_runs ORDER BY started_at DESC LIMIT ?"
            params = (limit,)
        async with db.execute(sql, params) as cur:
            rows = await cur.fetchall()
    results = []
    for row in rows:
        if row[0]:
            try:
                results.append(BenchmarkReport.model_validate_json(row[0]))
            except Exception:
                pass
    return results
