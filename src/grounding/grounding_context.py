"""Grounding context and summary utilities.

Sprint 9 — Wire Grounding into Generation Flow.
Provides GroundingContext dataclass and summary-building utilities.
No LLM calls.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.schema.persona import PersonaRecord
    from src.schema.cohort import GroundingSummary
    from src.grounding.types import GroundingResult


@dataclass
class GroundingContext:
    """Captures grounding inputs for a persona generation session.

    Attach to an ICPSpec or pass alongside assemble_cohort() to carry
    domain data through the generation pipeline.
    """
    domain_data: list[str] = field(default_factory=list)
    """Raw text strings (reviews, posts) to extract signals from."""

    domain: str = "general"
    """Domain label (for reporting purposes)."""

    @property
    def has_data(self) -> bool:
        """True if domain_data is non-empty."""
        return bool(self.domain_data)

    @property
    def data_count(self) -> int:
        """Number of raw text strings provided."""
        return len(self.domain_data)


def compute_tendency_source_distribution(personas: list) -> dict[str, float]:
    """Compute tendency source distribution across a list of PersonaRecord objects.

    Inspects price_sensitivity.source, switching_propensity.source,
    and trust_orientation.source for each persona.

    Returns:
        dict with exactly keys {"grounded", "proxy", "estimated"},
        values are fractions in [0.0, 1.0] summing to 1.0.

    If personas is empty or no sources found, returns {"grounded": 0.0, "proxy": 1.0, "estimated": 0.0}.
    """
    tendency_sources: list[str] = []
    for p in personas:
        bt = getattr(p, "behavioural_tendencies", None)
        if bt is None:
            continue
        for field_name in ("price_sensitivity", "switching_propensity", "trust_orientation"):
            obj = getattr(bt, field_name, None)
            if obj is not None:
                src = getattr(obj, "source", None)
                if src is not None:
                    tendency_sources.append(src)

    if not tendency_sources:
        return {"grounded": 0.0, "proxy": 1.0, "estimated": 0.0}

    total = len(tendency_sources)
    source_counts = Counter(tendency_sources)

    dist = {
        "grounded": round(source_counts.get("grounded", 0) / total, 6),
        "proxy": round(source_counts.get("proxy", 0) / total, 6),
        "estimated": round(source_counts.get("estimated", 0) / total, 6),
    }

    # Correct rounding drift so values sum exactly to 1.0
    _sum = sum(dist.values())
    if abs(_sum - 1.0) > 1e-9:
        largest_key = max(dist, key=lambda k: dist[k])
        dist[largest_key] = round(dist[largest_key] + (1.0 - _sum), 9)

    return dist


def build_grounding_summary_from_result(result) -> "GroundingSummary":
    """Build a GroundingSummary from a GroundingResult.

    Args:
        result: GroundingResult from run_grounding_pipeline().

    Returns:
        Validated GroundingSummary (Pydantic model).

    Raises:
        ImportError: if src.schema.cohort is not available.
    """
    from src.schema.cohort import GroundingSummary

    dist = compute_tendency_source_distribution(result.personas)

    return GroundingSummary(
        tendency_source_distribution=dist,
        domain_data_signals_extracted=result.signals_extracted,
        clusters_derived=result.clusters_derived,
    )
