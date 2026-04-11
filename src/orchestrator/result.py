"""
PersonaGenerationResult — the structured output contract.

Every successful invocation of invoke_persona_generator() returns one of these.
It is JSON-serialisable via .to_dict() / .to_json() and can be saved to disk
via .save(path).

Usage::

    result = await invoke_persona_generator(brief)

    print(result.summary)
    print(f"Cost: ${result.cost_actual.total:.2f}")
    print(f"Personas: {len(result.personas)}")
    result.save("./outputs/littlejoys-run.json")
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CostActual:
    """Actual cost breakdown after a run completes."""

    def __init__(
        self,
        pre_generation: float = 0.0,
        generation: float = 0.0,
        simulation: float = 0.0,
    ) -> None:
        self.pre_generation = pre_generation
        self.generation = generation
        self.simulation = simulation

    @property
    def total(self) -> float:
        return self.pre_generation + self.generation + self.simulation

    def per_persona(self, count: int) -> float:
        return self.total / max(count, 1)

    def to_dict(self) -> dict[str, float]:
        return {
            "pre_generation": round(self.pre_generation, 4),
            "generation": round(self.generation, 4),
            "simulation": round(self.simulation, 4),
            "total": round(self.total, 4),
        }


class QualityReport:
    """Post-generation quality gate summary."""

    def __init__(
        self,
        gates_passed: list[str] | None = None,
        gates_failed: list[str] | None = None,
        personas_quarantined: int = 0,
        personas_regenerated: int = 0,
        distinctiveness_score: float | None = None,
        grounding_state: str = "ungrounded",
        contamination_findings: list[dict] | None = None,
    ) -> None:
        self.gates_passed = gates_passed or []
        self.gates_failed = gates_failed or []
        self.personas_quarantined = personas_quarantined
        self.personas_regenerated = personas_regenerated
        self.distinctiveness_score = distinctiveness_score
        self.grounding_state = grounding_state
        self.contamination_findings = contamination_findings or []

    @property
    def all_passed(self) -> bool:
        return len(self.gates_failed) == 0 and self.personas_quarantined == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "gates_passed": self.gates_passed,
            "gates_failed": self.gates_failed,
            "all_passed": self.all_passed,
            "personas_quarantined": self.personas_quarantined,
            "personas_regenerated": self.personas_regenerated,
            "distinctiveness_score": self.distinctiveness_score,
            "grounding_state": self.grounding_state,
            "contamination_findings": self.contamination_findings,
        }


class PersonaGenerationResult:
    """Complete output from a persona generation + optional simulation run."""

    def __init__(
        self,
        run_id: str,
        cohort_id: str,
        client: str,
        domain: str,
        tier_used: str,
        count_requested: int,
        count_delivered: int,
        cost_actual: CostActual,
        quality_report: QualityReport,
        personas: list[dict],
        cohort_envelope: dict,
        simulation_results: dict | None = None,
        pipeline_doc_path: str | None = None,
        cohort_file_path: str | None = None,
        generated_at: datetime | None = None,
        wall_clock_seconds: float | None = None,
    ) -> None:
        self.run_id = run_id
        self.cohort_id = cohort_id
        self.client = client
        self.domain = domain
        self.tier_used = tier_used
        self.count_requested = count_requested
        self.count_delivered = count_delivered
        self.cost_actual = cost_actual
        self.quality_report = quality_report
        self.personas = personas
        self.cohort_envelope = cohort_envelope
        self.simulation_results = simulation_results
        self.pipeline_doc_path = pipeline_doc_path
        self.cohort_file_path = cohort_file_path
        self.generated_at = generated_at or datetime.now(timezone.utc)
        self.wall_clock_seconds = wall_clock_seconds

    # ── Convenience properties ─────────────────────────────────────────────

    @property
    def summary(self) -> str:
        """One-line human-readable result summary."""
        status = "✓ All quality gates passed" if self.quality_report.all_passed \
            else f"⚠ {len(self.quality_report.gates_failed)} gate(s) failed"
        sim_str = ""
        if self.simulation_results:
            sim_str = f" + simulation run."
        return (
            f"{self.count_delivered} {self.tier_used.upper()} personas for "
            f"{self.client} ({self.domain}){sim_str}  "
            f"{status}.  "
            f"Cost: ${self.cost_actual.total:.2f}  "
            f"({self.quality_report.grounding_state})"
        )

    @property
    def cost_per_persona(self) -> float:
        return self.cost_actual.per_persona(self.count_delivered)

    # ── Serialisation ──────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "cohort_id": self.cohort_id,
            "client": self.client,
            "domain": self.domain,
            "generated_at": self.generated_at.isoformat(),
            "tier_used": self.tier_used,
            "count_requested": self.count_requested,
            "count_delivered": self.count_delivered,
            "wall_clock_seconds": round(self.wall_clock_seconds or 0, 1),
            "cost_actual": self.cost_actual.to_dict(),
            "cost_per_persona": round(self.cost_per_persona, 4),
            "quality_report": self.quality_report.to_dict(),
            "pipeline_doc_path": self.pipeline_doc_path,
            "cohort_file_path": self.cohort_file_path,
            "simulation_results": self.simulation_results,
            "summary": self.summary,
            # Persona records are the full output — included last for readability
            "cohort_envelope": self.cohort_envelope,
            "personas": self.personas,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, path: str | Path) -> Path:
        """Write result JSON to disk.  Creates parent directories as needed."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json())
        return p

    # ── Persona accessors ──────────────────────────────────────────────────

    def get_persona(self, persona_id: str) -> dict | None:
        for p in self.personas:
            if p.get("persona_id") == persona_id:
                return p
        return None

    def persona_ids(self) -> list[str]:
        return [p.get("persona_id", "") for p in self.personas]

    def __repr__(self) -> str:
        return (
            f"PersonaGenerationResult("
            f"run_id={self.run_id!r}, "
            f"count={self.count_delivered}, "
            f"tier={self.tier_used!r}, "
            f"cost=${self.cost_actual.total:.2f})"
        )
