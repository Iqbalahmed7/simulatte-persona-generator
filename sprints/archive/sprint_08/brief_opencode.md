# SPRINT 8 BRIEF — OPENCODE
**Role:** Grounding Types + Pipeline Orchestrator + Pipeline Tests
**Sprint:** 8 — Grounding Pipeline
**Spec ref:** Master Spec §7 (Grounding Strategy), §14 (S15 build order)
**Previous rating:** 19/20

---

## Context

Sprint 7 delivered temporal simulation. Sprint 8 builds the Grounding Pipeline — the mechanism that takes raw domain data (reviews, posts) and upgrades persona `BehaviouralTendencies` from `source="proxy"` to `source="grounded"`.

The pipeline has 4 stages (per §7):
1. Signal extraction (Cursor) — text → tagged Signal objects
2. Feature construction (Goose) — signals → BehaviouralFeatures aggregate
3. Cluster derivation (Codex) — per-signal feature vectors → BehaviouralArchetype list (pure-Python K-means)
4. Tendency assignment (Goose) — nearest archetype → updated PersonaRecord

**Your job:** Write the shared type definitions (types.py), the pipeline orchestrator (pipeline.py), and structural pipeline tests.

---

## File 1: `src/grounding/types.py`

This file is the shared contract. All other engineers import from it. Write it exactly as specified — field names and types are canonical.

```python
"""Shared type definitions for the Grounding Pipeline.

Sprint 8 — Grounding Pipeline.
No LLM calls. Pure data types only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# --- Signal types ---

SignalType = Literal[
    "purchase_trigger",
    "rejection",
    "switching",
    "trust_citation",
    "price_mention",
]


@dataclass
class Signal:
    """A single decision-language signal extracted from raw text."""
    id: str
    text: str
    signal_type: SignalType
    platform: str | None = None
    rating: int | None = None    # 1–5 star rating if available
    date: str | None = None
    category: str | None = None


# --- Feature types ---

@dataclass
class BehaviouralFeatures:
    """Aggregate behavioural features computed from a Signal list.

    All proportion fields must be in [0.0, 1.0].
    """
    price_salience_index: float          # price_mention count / total signals
    trust_source_distribution: dict[str, float]   # expert/peer/brand/ad/community keys
    switching_trigger_taxonomy: dict[str, float]  # price/feature/service/competitive/life_change
    purchase_trigger_taxonomy: dict[str, float]   # need/recommendation/trial/promotion/event
    objection_cluster_frequencies: dict[str, float]  # price/trust/information keys
    signal_count: int

    def to_vector(self) -> list[float]:
        """Flatten to a fixed 9-dim vector for clustering input.

        Dimensions (in order):
          0: price_salience_index
          1: trust_source_distribution["expert"]
          2: trust_source_distribution["peer"]
          3: trust_source_distribution["brand"]
          4: trust_source_distribution["community"]
          5: switching_trigger_taxonomy["price"]
          6: switching_trigger_taxonomy["service"]
          7: purchase_trigger_taxonomy["need"]
          8: purchase_trigger_taxonomy["recommendation"]
        """
        td = self.trust_source_distribution
        sw = self.switching_trigger_taxonomy
        pt = self.purchase_trigger_taxonomy
        return [
            self.price_salience_index,
            td.get("expert", 0.0),
            td.get("peer", 0.0),
            td.get("brand", 0.0),
            td.get("community", 0.0),
            sw.get("price", 0.0),
            sw.get("service", 0.0),
            pt.get("need", 0.0),
            pt.get("recommendation", 0.0),
        ]


# --- Archetype types ---

@dataclass
class BehaviouralArchetype:
    """A behavioural cluster archetype derived from K-means clustering."""
    archetype_id: str
    size: int                                    # number of signals in this cluster
    price_sensitivity_band: Literal["low", "medium", "high", "extreme"]
    trust_orientation_weights: dict[str, float]  # expert/peer/brand/ad/community/influencer
    switching_propensity_band: Literal["low", "medium", "high"]
    primary_objections: list[str]
    centroid: list[float]                        # 9-dim feature vector centroid


# --- Pipeline result ---

@dataclass
class GroundingResult:
    """Result of running the full grounding pipeline."""
    personas: list                           # list[PersonaRecord] — updated with grounded tendencies
    archetypes: list[BehaviouralArchetype]
    signals_extracted: int
    clusters_derived: int
    warning: str | None = None               # populated if signal_count < 200
```

---

## File 2: `src/grounding/__init__.py`

```python
"""Grounding pipeline for Simulatte Persona Generator.

Sprint 8 — upgrades BehaviouralTendencies from proxy to grounded
using domain data (reviews, posts).
"""
```

---

## File 3: `src/grounding/pipeline.py`

```python
"""Grounding pipeline orchestrator.

Sprint 8 — Grounding Pipeline.
Coordinates all 4 stages: extract → construct → cluster → assign.
No LLM calls.
"""
from __future__ import annotations

from src.grounding.types import GroundingResult, BehaviouralFeatures

MIN_SIGNALS_THRESHOLD = 200


def run_grounding_pipeline(
    raw_texts: list[str],
    personas: list,           # list[PersonaRecord]
    domain: str = "general",
) -> GroundingResult:
    """Run the full grounding pipeline.

    Args:
        raw_texts: List of raw text strings (reviews, posts, etc.)
        personas: List of PersonaRecord objects whose tendencies will be updated.
        domain: Domain label (for metadata only).

    Returns:
        GroundingResult with updated personas and derived archetypes.

    Raises:
        ValueError: If raw_texts is empty.
    """
    ...
```

### Implementation logic:

```python
def run_grounding_pipeline(raw_texts, personas, domain="general"):
    from src.grounding.signal_extractor import extract_signals, signals_to_vectors
    from src.grounding.feature_constructor import construct_features
    from src.grounding.cluster_deriver import derive_clusters
    from src.grounding.tendency_assigner import assign_grounded_tendencies

    if not raw_texts:
        raise ValueError("raw_texts must not be empty")

    # Stage 1: Extract signals
    signals = extract_signals(raw_texts)

    # Stage 2: Construct aggregate features
    features = construct_features(signals)

    # Stage 3: Cluster — one vector per signal
    vectors = signals_to_vectors(signals)
    archetypes = derive_clusters(vectors)

    # Stage 4: Assign grounded tendencies to each persona
    updated_personas = [
        assign_grounded_tendencies(persona, archetypes)
        for persona in personas
    ]

    warning = None
    if len(signals) < MIN_SIGNALS_THRESHOLD:
        warning = (
            f"Only {len(signals)} signals extracted (threshold: {MIN_SIGNALS_THRESHOLD}). "
            f"Results may be unstable. Consider providing more domain data."
        )

    return GroundingResult(
        personas=updated_personas,
        archetypes=archetypes,
        signals_extracted=len(signals),
        clusters_derived=len(archetypes),
        warning=warning,
    )
```

---

## File 4: `tests/test_grounding_pipeline.py`

### Test 1: Pipeline raises on empty input

```python
def test_pipeline_raises_on_empty_texts():
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    import pytest
    with pytest.raises(ValueError, match="empty"):
        run_grounding_pipeline([], [persona])
```

### Test 2: Pipeline returns correct shape

```python
def test_pipeline_returns_correct_shape():
    """
    5 texts, 2 personas → GroundingResult with:
    - 2 updated personas
    - archetypes derived
    - signals_extracted > 0
    - clusters_derived == len(archetypes)
    """
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = [
        "I bought this because my friend recommended it.",
        "Too expensive, I avoided it.",
        "Switched from my usual brand due to the high price.",
        "A trusted expert reviewed this positively.",
        "The price point was reasonable so I tried it.",
    ]
    personas = [make_synthetic_persona(), make_synthetic_persona()]
    result = run_grounding_pipeline(texts, personas)

    assert result.signals_extracted > 0
    assert result.clusters_derived == len(result.archetypes)
    assert len(result.personas) == 2
```

### Test 3: Warning fires below threshold

```python
def test_pipeline_warning_below_threshold():
    """
    Fewer than 200 texts → warning string populated.
    """
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = [
        "I switched brands because the price was too high.",
        "A friend told me to try this product.",
        "Bought it on sale.",
    ]
    result = run_grounding_pipeline(texts, [make_synthetic_persona()])
    assert result.warning is not None
    assert "200" in result.warning
```

### Test 4: Pipeline with empty personas list

```python
def test_pipeline_with_no_personas():
    """Zero personas is valid — pipeline still runs signal/cluster stages."""
    from src.grounding.pipeline import run_grounding_pipeline

    texts = [
        "I bought this because it was on sale.",
        "Switched from my usual brand — the price doubled.",
        "A trusted friend recommended it.",
    ]
    result = run_grounding_pipeline(texts, [])
    assert result.signals_extracted > 0
    assert len(result.personas) == 0
```

### Test 5: Grounded tendencies have correct source

```python
def test_pipeline_upgrades_tendency_source():
    """
    After pipeline runs, at least one tendency on each persona
    should carry source='grounded'.
    """
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = [
        "I always check the price before buying — bought after a discount.",
        "Switched brands because this one was cheaper.",
        "A peer recommended this and I trusted them.",
        "Too expensive, I rejected it outright.",
        "Found this through an expert review — decided to buy.",
    ] * 5  # 25 signals total

    persona = make_synthetic_persona()
    result = run_grounding_pipeline(texts, [persona])

    updated = result.personas[0]
    bt = updated.behavioural_tendencies
    sources = {
        bt.price_sensitivity.source,
        bt.trust_orientation.source,
        bt.switching_propensity.source,
    }
    assert "grounded" in sources, (
        f"Expected at least one grounded tendency. Got sources: {sources}"
    )
```

---

## Constraints

- No LLM calls anywhere in this file.
- Import all stage functions lazily (inside the function body) to avoid circular imports.
- `run_grounding_pipeline` must handle the case where `personas` is an empty list.
- `types.py` must be importable with zero side effects.

---

## Outcome File

When done, write `sprints/outcome_opencode.md` with:
1. Files created (line counts)
2. types.py — list all exported types
3. pipeline.py — stage wiring description
4. Test results (pass/fail for all 5 tests)
5. Known gaps
