"""Unit test for the cohort_persistence helper using SQLite + JSONB→JSON shim."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def test_persist_cohort_extracts_warnings_and_personas():
    from sqlalchemy import create_engine
    from sqlalchemy.dialects.postgresql import JSONB, UUID
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.orm import sessionmaker

    @compiles(JSONB, "sqlite")
    def _j(_t, _c, **_kw):  # noqa: ANN001
        return "JSON"

    @compiles(UUID, "sqlite")
    def _u(_t, _c, **_kw):  # noqa: ANN001
        return "VARCHAR(36)"

    from src.db.session import Base
    import src.db.models  # noqa: F401
    from src.db.cohort_persistence import persist_cohort

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)

    envelope = {
        "cohort_id": "legacy-cohort-abc",
        "domain": "cpg",
        "client": "test",
        "personas": [
            {"persona_id": "p1", "name": "Alice", "age": 30},
            {"persona_id": "p2", "name": "Bob", "age": 42},
        ],
        "gate_results": [
            {"gate": "G6", "passed": False, "reason": "stub variance"},
            {"gate": "G7", "passed": True},
        ],
        "gate_waivers": [],
    }

    with Session() as s:
        cohort = persist_cohort(
            s,
            tenant_id="t1",
            brief={"n": 2},
            cohort_envelope=envelope,
            cost_usd=1.23,
            generator_version="test",
        )
        s.refresh(cohort)
        assert cohort.tenant_id == "t1"
        assert cohort.status == "complete"
        assert cohort.gate_warnings == ["G6: stub variance"]
        assert float(cohort.total_cost_usd) == pytest.approx(1.23)
        assert len(cohort.personas) == 2
        assert cohort.personas[0].persona_index == 0
        assert cohort.personas[0].dossier_snapshot["name"] == "Alice"
