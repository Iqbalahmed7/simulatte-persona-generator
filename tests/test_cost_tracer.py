from __future__ import annotations

import asyncio
import csv

import pytest

from src.observability.cost_tracer import CostTracer, LLMCallRecord


@pytest.fixture(autouse=True)
def _reset_cost_tracer() -> None:
    CostTracer.reset()
    yield
    CostTracer.reset()


@pytest.mark.asyncio
async def test_concurrency_safety() -> None:
    async def _worker(idx: int) -> None:
        persona_id = f"persona-{idx}"
        CostTracer.start_persona(persona_id)
        CostTracer.set_phase("attribute_fill")
        for j in range(5):
            CostTracer.record(
                LLMCallRecord(
                    persona_id=CostTracer.current_persona_id(),
                    phase=CostTracer.current_phase(),
                    sub_step=f"attr-{j}",
                    input_tokens=10 + j,
                    output_tokens=5 + j,
                    duration_ms=30 + j,
                    timestamp=1_700_000_000.0 + j,
                    model="claude-haiku-4.5",
                    status="ok",
                )
            )
        summary = CostTracer.finish_persona(persona_id)
        assert summary.total_calls == 5

    await asyncio.gather(*[_worker(i) for i in range(10)])
    records = CostTracer.all_records()
    assert len(records) == 50

    counts: dict[str, int] = {}
    for rec in records:
        counts[rec.persona_id] = counts.get(rec.persona_id, 0) + 1
    assert all(v == 5 for v in counts.values())


def test_csv_round_trip(tmp_path) -> None:
    expected: list[LLMCallRecord] = []
    for i in range(100):
        rec = LLMCallRecord(
            persona_id=f"p-{i % 7}",
            phase="life_story" if i % 2 == 0 else "attribute_fill",
            sub_step=f"step-{i}",
            input_tokens=i,
            output_tokens=i + 1,
            duration_ms=100 + i,
            timestamp=1_700_000_000.0 + i,
            model="claude-haiku-4.5",
            status="ok",
        )
        expected.append(rec)
        CostTracer.record(rec)

    out = tmp_path / "trace.csv"
    CostTracer.dump_csv(out)

    with out.open(newline="", encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))

    assert len(rows) == len(expected)
    for row, rec in zip(rows, expected):
        assert row["persona_id"] == rec.persona_id
        assert row["phase"] == rec.phase
        assert row["sub_step"] == rec.sub_step
        assert int(row["input_tokens"]) == rec.input_tokens
        assert int(row["output_tokens"]) == rec.output_tokens
        assert int(row["duration_ms"]) == rec.duration_ms
        assert float(row["timestamp"]) == rec.timestamp
        assert row["model"] == rec.model
        assert row["status"] == rec.status


def test_summary_math_matches_haiku_pricing() -> None:
    persona_id = "p-1"
    CostTracer.record(
        LLMCallRecord(
            persona_id=persona_id,
            phase="identity_core",
            sub_step="worldview",
            input_tokens=1_000_000,
            output_tokens=100_000,
            duration_ms=200,
            timestamp=1.0,
            model="claude-haiku-4.5",
            status="ok",
        )
    )
    CostTracer.record(
        LLMCallRecord(
            persona_id=persona_id,
            phase="identity_behavior",
            sub_step="risk_appetite",
            input_tokens=0,
            output_tokens=100_000,
            duration_ms=120,
            timestamp=2.0,
            model="claude-haiku-4.5",
            status="ok",
        )
    )

    summary = CostTracer.finish_persona(persona_id)
    assert summary.total_calls == 2
    assert summary.total_input_tokens == 1_000_000
    assert summary.total_output_tokens == 200_000
    assert summary.estimated_cost_usd == pytest.approx(2.0, rel=1e-6)


@pytest.mark.asyncio
async def test_contextvar_propagation_nested_async() -> None:
    async def _inner() -> str:
        await asyncio.sleep(0)
        return CostTracer.current_persona_id()

    CostTracer.start_persona("persona-nested")
    assert await _inner() == "persona-nested"


def test_reset_clears_state() -> None:
    CostTracer.start_persona("persona-reset")
    CostTracer.set_phase("life_story")
    CostTracer.record(
        LLMCallRecord(
            persona_id="persona-reset",
            phase="life_story",
            sub_step="generate",
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
            timestamp=1.0,
            model="claude-haiku-4.5",
            status="ok",
        )
    )
    CostTracer.reset()

    assert CostTracer.current_persona_id() == "unknown"
    assert CostTracer.current_phase() == "other"
    assert CostTracer.all_records() == []
