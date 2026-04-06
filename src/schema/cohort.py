from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from src.schema.persona import Mode, PersonaRecord, TendencySource


class TaxonomyMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_attributes: int
    domain_extension_attributes: int
    total_attributes: int
    domain_data_used: bool
    business_problem: str = ""
    icp_spec_hash: str = ""


class CohortSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_style_distribution: dict
    trust_anchor_distribution: dict
    risk_appetite_distribution: dict
    consistency_scores: dict
    persona_type_distribution: dict
    distinctiveness_score: float
    coverage_assessment: str
    dominant_tensions: list[str]


class GroundingSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tendency_source_distribution: dict[str, float]
    domain_data_signals_extracted: int
    clusters_derived: int

    @field_validator("tendency_source_distribution")
    @classmethod
    def _validate_tendency_source_distribution(cls, v: dict[str, float]) -> dict[str, float]:
        required_keys = {k for k in TendencySource.__args__}  # type: ignore[attr-defined]
        if set(v.keys()) != required_keys:
            raise ValueError(
                "tendency_source_distribution must have exactly keys: grounded, proxy, estimated"
            )
        total = sum(float(x) for x in v.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError("tendency_source_distribution values must sum to 1.0")
        for key, value in v.items():
            fv = float(value)
            if not (0.0 <= fv <= 1.0):
                raise ValueError(f"tendency_source_distribution[{key}] must be 0.0-1.0")
            v[key] = fv
        return v


CalibrationStatus = Literal[
    "uncalibrated",
    "benchmark_calibrated",
    "client_calibrated",
    "calibration_failed",
]


class CalibrationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CalibrationStatus
    method_applied: str | None = None
    last_calibrated: datetime | None = None
    benchmark_source: str | None = None
    notes: str | None = None


class CohortEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cohort_id: str
    generated_at: datetime
    domain: str
    client: str = ""          # Client name — used by G12 grounding check to load market facts
    business_problem: str
    mode: Mode
    icp_spec_hash: str
    taxonomy_used: TaxonomyMeta
    personas: list[PersonaRecord]
    cohort_summary: CohortSummary
    grounding_summary: GroundingSummary
    calibration_state: CalibrationState

