"""Background worker — polls calibration_jobs for queued rows and runs them.

Run with:
    python scripts/calibration_worker.py

Configuration via env vars:
    DATABASE_URL          — Postgres URL (required)
    WORKER_POLL_INTERVAL  — seconds between polls when queue is empty (default 5)
    WORKER_MAX_RUNS       — exit after N jobs (default 0 = run forever)
    LOG_LEVEL             — logging level (default INFO)
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import time
from pathlib import Path

# Make `src.*` importable when run from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from src.db.models import CalibrationJob  # noqa: E402
from src.db.session import get_session_sync, init_engine  # noqa: E402
from src.worker.calibration_runner import run_job  # noqa: E402

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s :: %(message)s"
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format=LOG_FORMAT,
    stream=sys.stdout,
)
logger = logging.getLogger("calibration_worker")

_RUNNING = True


def _claim_next_job() -> "CalibrationJob | None":
    """Atomically claim the next queued job using SELECT ... FOR UPDATE SKIP LOCKED."""
    with get_session_sync() as session:
        with session.begin():
            row = session.execute(
                text(
                    """
                    SELECT id FROM calibration_jobs
                    WHERE status = 'queued'
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """
                )
            ).first()
            if row is None:
                return None
            job = session.get(CalibrationJob, row[0])
            if job is None:
                return None
            job.status = "claimed"
            session.flush()
            session.expunge(job)
            return job


def _process_one(job_id) -> None:
    with get_session_sync() as session:
        job = session.get(CalibrationJob, job_id)
        if job is None:
            logger.warning("Claimed job %s vanished", job_id)
            return
        run_job(session, job)


def main() -> int:
    init_engine()
    poll = float(os.environ.get("WORKER_POLL_INTERVAL", "5"))
    max_runs = int(os.environ.get("WORKER_MAX_RUNS", "0"))
    runs = 0

    def _stop(_signum, _frame):
        global _RUNNING
        logger.info("Received stop signal, finishing current job…")
        _RUNNING = False

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    logger.info("Calibration worker started (poll=%.1fs, max_runs=%d)", poll, max_runs)
    while _RUNNING:
        try:
            claimed = _claim_next_job()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Claim failed: %s", exc)
            time.sleep(poll)
            continue

        if claimed is None:
            time.sleep(poll)
            continue

        logger.info("Processing job %s", claimed.id)
        try:
            _process_one(claimed.id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Worker error processing %s: %s", claimed.id, exc)
        runs += 1
        if max_runs and runs >= max_runs:
            logger.info("Reached WORKER_MAX_RUNS=%d, exiting", max_runs)
            break

    logger.info("Worker exiting cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
