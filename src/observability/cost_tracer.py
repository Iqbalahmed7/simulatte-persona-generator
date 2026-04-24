"""Async-aware per-call cost tracing for LLM operations."""

from __future__ import annotations

import csv
import logging
import time
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

PhaseType = Literal[
    "life_story",
    "identity_core",
    "identity_behavior",
    "attribute_fill",
    "scenario_perceive",
    "scenario_accumulate",
    "scenario_decide",
    "other",
]

_LOGGER = logging.getLogger(__name__)

_INPUT_COST_PER_TOKEN = 1.0 / 1_000_000
_OUTPUT_COST_PER_TOKEN = 5.0 / 1_000_000


@dataclass(frozen=True)
class LLMCallRecord:
    persona_id: str
    phase: str
    sub_step: str
    input_tokens: int
    output_tokens: int
    duration_ms: int
    timestamp: float
    model: str
    status: Literal["ok", "retry", "fail"]


@dataclass
class PersonaCostSummary:
    persona_id: str
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_duration_ms: int
    by_phase: dict[str, dict]
    estimated_cost_usd: float


class CostTracer:
    """Thread-safe, async-aware cost tracer using contextvars."""

    _records: list[LLMCallRecord] = []
    _persona_id: ContextVar[str] = ContextVar("persona_id", default="unknown")
    _phase: ContextVar[str] = ContextVar("phase", default="other")

    @classmethod
    def start_persona(cls, persona_id: str) -> None:
        cls._persona_id.set(persona_id)

    @classmethod
    def set_phase(cls, phase: PhaseType) -> None:
        cls._phase.set(phase)

    @classmethod
    def current_persona_id(cls) -> str:
        return cls._persona_id.get()

    @classmethod
    def current_phase(cls) -> str:
        return cls._phase.get()

    @classmethod
    def record(cls, rec: LLMCallRecord) -> None:
        cls._records.append(rec)

    @classmethod
    def finish_persona(cls, persona_id: str) -> PersonaCostSummary:
        persona_records = [r for r in cls._records if r.persona_id == persona_id]
        by_phase: dict[str, dict] = {}
        total_calls = len(persona_records)
        total_input_tokens = 0
        total_output_tokens = 0
        total_duration_ms = 0

        for rec in persona_records:
            total_input_tokens += rec.input_tokens
            total_output_tokens += rec.output_tokens
            total_duration_ms += rec.duration_ms
            phase_stats = by_phase.setdefault(
                rec.phase,
                {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "duration_ms": 0,
                },
            )
            phase_stats["calls"] += 1
            phase_stats["input_tokens"] += rec.input_tokens
            phase_stats["output_tokens"] += rec.output_tokens
            phase_stats["duration_ms"] += rec.duration_ms

        estimated_cost_usd = (
            (total_input_tokens * _INPUT_COST_PER_TOKEN)
            + (total_output_tokens * _OUTPUT_COST_PER_TOKEN)
        )

        return PersonaCostSummary(
            persona_id=persona_id,
            total_calls=total_calls,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_duration_ms=total_duration_ms,
            by_phase=by_phase,
            estimated_cost_usd=estimated_cost_usd,
        )

    @classmethod
    def all_records(cls) -> list[LLMCallRecord]:
        return list(cls._records)

    @classmethod
    def dump_csv(cls, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(
                fp,
                fieldnames=[
                    "persona_id",
                    "phase",
                    "sub_step",
                    "input_tokens",
                    "output_tokens",
                    "duration_ms",
                    "timestamp",
                    "model",
                    "status",
                ],
            )
            writer.writeheader()
            for rec in cls._records:
                writer.writerow(asdict(rec))
        _LOGGER.info("cost_trace_written | path=%s rows=%d", path, len(cls._records))

    @classmethod
    def reset(cls) -> None:
        cls._records.clear()
        cls._persona_id.set("unknown")
        cls._phase.set("other")


def usage_to_token_counts(usage: object) -> tuple[int, int]:
    """Extract (input_tokens, output_tokens) from varied SDK usage shapes."""
    if usage is None:
        return (0, 0)

    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    if input_tokens is None and isinstance(usage, dict):
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")

    try:
        return (int(input_tokens or 0), int(output_tokens or 0))
    except (TypeError, ValueError):
        return (0, 0)


def make_record(
    *,
    sub_step: str,
    model: str,
    started_monotonic: float,
    status: Literal["ok", "retry", "fail"],
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> LLMCallRecord:
    """Build a standard LLMCallRecord from ambient contextvars."""
    return LLMCallRecord(
        persona_id=CostTracer.current_persona_id(),
        phase=CostTracer.current_phase(),
        sub_step=sub_step,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_ms=int((time.monotonic() - started_monotonic) * 1000),
        timestamp=time.time(),
        model=model,
        status=status,
    )
