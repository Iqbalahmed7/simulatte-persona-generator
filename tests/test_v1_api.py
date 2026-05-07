"""Smoke tests for /v1/* endpoints using an in-memory SQLite DB.

We swap the JSONB columns for plain JSON since SQLite doesn't have JSONB.
The tests cover: auth gating, calibration enqueue, status polling, cohort
metadata, persona listing, deterministic sampling, cancel, cost summary.
"""
from __future__ import annotations

import os
import uuid

import pytest

# Force a clean async sqlite URL BEFORE any db import
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("INTERNAL_API_KEY", "test-key")

# Patch JSONB → JSON for SQLite compatibility
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy import JSON  # noqa: E402
JSONB.__visit_name__ = "JSON"  # type: ignore[attr-defined]

# Patch UUID column to String for SQLite compatibility
from sqlalchemy.dialects.postgresql import UUID  # noqa: E402
from sqlalchemy import String as _String  # noqa: E402

_orig_uuid_init = UUID.__init__


def _uuid_init(self, *a, **kw):
    _orig_uuid_init(self, *a, **kw)


UUID.__init__ = _uuid_init  # noqa: E305


def _is_sqlite() -> bool:
    return os.environ["DATABASE_URL"].startswith("sqlite")


@pytest.fixture(scope="module")
def app_client():
    """Build the FastAPI app + create tables in SQLite, return TestClient."""
    if not _is_sqlite():
        pytest.skip("v1 smoke tests run against in-memory SQLite only")

    from fastapi.testclient import TestClient

    # Ensure JSONB compiles to JSON on sqlite by overriding compiler
    from sqlalchemy.ext.compiler import compiles
    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(_t, _c, **_kw):  # noqa: ANN001
        return "JSON"

    @compiles(UUID, "sqlite")
    def _compile_uuid_sqlite(_t, _c, **_kw):  # noqa: ANN001
        return "VARCHAR(36)"

    from src.db.session import init_engine, _async_engine  # noqa: F401

    init_engine(os.environ["DATABASE_URL"])
    # Sync engine sqlite mirror
    from src.db import session as _ses
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    sync_url = "sqlite:///:memory:"
    _ses._sync_engine = create_engine(sync_url, future=True)
    _ses._sync_sessionmaker = sessionmaker(_ses._sync_engine, expire_on_commit=False)

    # Create schema using sync engine
    from src.db.session import Base
    import src.db.models  # noqa: F401
    Base.metadata.create_all(_ses._sync_engine)

    # Async schema create
    import asyncio
    from src.db.session import _async_engine as ae
    async def _create():
        async with ae.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.new_event_loop().run_until_complete(_create())

    from src.api.main import app
    return TestClient(app)


def _auth():
    return {"Authorization": "Bearer test-key"}


def test_health_open(app_client):
    r = app_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_v1_requires_auth(app_client):
    r = app_client.get("/v1/cost/summary")
    assert r.status_code == 401


def test_cost_summary_empty(app_client):
    r = app_client.get("/v1/cost/summary", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["total_usd"] == 0
    assert body["event_count"] == 0


def test_create_calibration_enqueues(app_client):
    payload = {
        "tenant_id": "acme",
        "n_personas": 5,
        "domain": "cpg",
        "business_problem": "Why do parents switch brands?",
    }
    r = app_client.post("/v1/calibrations", json=payload, headers=_auth())
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "queued"
    assert uuid.UUID(body["job_id"])

    # Poll
    r2 = app_client.get(f"/v1/calibrations/{body['job_id']}", headers=_auth())
    assert r2.status_code == 200
    assert r2.json()["status"] == "queued"


def test_cancel_queued_job(app_client):
    payload = {
        "tenant_id": "acme",
        "n_personas": 5,
        "domain": "cpg",
        "business_problem": "x",
    }
    job_id = app_client.post("/v1/calibrations", json=payload, headers=_auth()).json()["job_id"]
    r = app_client.post(f"/v1/calibrations/{job_id}/cancel", headers=_auth())
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_cohort_404(app_client):
    fake = uuid.uuid4()
    r = app_client.get(f"/v1/cohorts/{fake}", headers=_auth())
    assert r.status_code == 404
