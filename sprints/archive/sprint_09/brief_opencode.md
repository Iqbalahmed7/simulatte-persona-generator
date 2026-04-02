# SPRINT 9 BRIEF — OPENCODE
**Role:** Grounding Context Helper + grounding_summary utility
**Sprint:** 9 — Wire Grounding into Generation Flow
**Spec ref:** Master Spec §7 (GroundingSummary population)
**Previous rating:** 20/20

---

## Context

Sprint 9 wires grounding into the generation flow. Your job is to write a helper module `src/grounding/grounding_context.py` that provides:

1. A `GroundingContext` dataclass — captures grounding inputs and state alongside an `ICPSpec`
2. A `build_grounding_summary_from_result()` function — converts a `GroundingResult` into a `GroundingSummary`
3. A `compute_tendency_source_distribution()` utility — computes the distribution dict from a list of personas

This module is a clean utility layer that the assembler and future callers can import rather than reimplementing the distribution math inline.

---

## File: `src/grounding/grounding_context.py`

```python
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
```

### Function 1: `compute_tendency_source_distribution`

```python
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
```

### Function 2: `build_grounding_summary_from_result`

```python
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
```

---

## Tests: `tests/test_grounding_context.py`

### Test 1: GroundingContext has_data

```python
def test_grounding_context_has_data():
    from src.grounding.grounding_context import GroundingContext
    ctx = GroundingContext(domain_data=["text 1", "text 2"])
    assert ctx.has_data is True
    assert ctx.data_count == 2
```

### Test 2: GroundingContext empty

```python
def test_grounding_context_empty():
    from src.grounding.grounding_context import GroundingContext
    ctx = GroundingContext()
    assert ctx.has_data is False
    assert ctx.data_count == 0
```

### Test 3: compute_tendency_source_distribution — all proxy

```python
def test_compute_distribution_all_proxy():
    from src.grounding.grounding_context import compute_tendency_source_distribution
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    personas = [make_synthetic_persona()]
    dist = compute_tendency_source_distribution(personas)

    assert set(dist.keys()) == {"grounded", "proxy", "estimated"}
    assert dist["grounded"] == 0.0
    assert dist["proxy"] > 0.0
    total = sum(dist.values())
    assert abs(total - 1.0) < 1e-6
```

### Test 4: compute_tendency_source_distribution — empty list

```python
def test_compute_distribution_empty_personas():
    from src.grounding.grounding_context import compute_tendency_source_distribution
    dist = compute_tendency_source_distribution([])
    assert dist == {"grounded": 0.0, "proxy": 1.0, "estimated": 0.0}
```

### Test 5: compute_tendency_source_distribution — sums to 1.0

```python
def test_compute_distribution_sums_to_one():
    """Regardless of mix, distribution must sum to 1.0."""
    from src.grounding.grounding_context import compute_tendency_source_distribution
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    personas = [make_synthetic_persona() for _ in range(5)]
    dist = compute_tendency_source_distribution(personas)
    total = sum(dist.values())
    assert abs(total - 1.0) < 1e-6
```

### Test 6: build_grounding_summary_from_result — correct field values

```python
def test_build_grounding_summary_from_result():
    """build_grounding_summary_from_result produces valid GroundingSummary."""
    from src.grounding.grounding_context import build_grounding_summary_from_result
    from src.grounding.types import GroundingResult, BehaviouralArchetype
    from src.schema.cohort import GroundingSummary
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    archetype = BehaviouralArchetype(
        archetype_id="arch-1",
        size=5,
        price_sensitivity_band="high",
        trust_orientation_weights={
            "expert": 0.6, "peer": 0.3, "brand": 0.2,
            "ad": 0.1, "community": 0.2, "influencer": 0.1,
        },
        switching_propensity_band="medium",
        primary_objections=["price_vs_value"],
        centroid=[0.7, 0.6, 0.3, 0.2, 0.2, 0.3, 0.2, 0.5, 0.3],
    )

    result = GroundingResult(
        personas=[make_synthetic_persona()],
        archetypes=[archetype],
        signals_extracted=42,
        clusters_derived=1,
    )

    summary = build_grounding_summary_from_result(result)

    assert isinstance(summary, GroundingSummary)
    assert summary.domain_data_signals_extracted == 42
    assert summary.clusters_derived == 1
    assert set(summary.tendency_source_distribution.keys()) == {"grounded", "proxy", "estimated"}
    total = sum(summary.tendency_source_distribution.values())
    assert abs(total - 1.0) < 1e-6
```

---

## Constraints

- No LLM calls.
- `grounding_context.py` must import `GroundingSummary` and `PersonaRecord` lazily (inside functions) to avoid circular imports.
- `compute_tendency_source_distribution()` must handle personas with missing fields gracefully (use `getattr(..., None)` pattern).
- 6 tests, all pass without `--integration`.
- Run full suite: must remain 91+ passed.

---

## Outcome File

When done, write `sprints/outcome_opencode.md` with:
1. File created (line count)
2. compute_tendency_source_distribution — approach
3. Rounding correction logic
4. Test results (6/6)
5. Full suite result
6. Known gaps
