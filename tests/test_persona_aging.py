"""tests/test_persona_aging.py — Longitudinal persona aging tests.

No LLM calls. All synthetic data.
Tests src/memory/aging.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.memory.aging import (
    AgingReport,
    _is_blocked_content,
    _cluster_reflections,
    _collect_reflections,
    run_annual_review,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_reflection(
    content: str,
    importance: int = 8,
    ref_id: str | None = None,
    source_ids: list[str] | None = None,
) -> MagicMock:
    r = MagicMock()
    r.id = ref_id or str(uuid.uuid4())
    r.content = content
    r.importance = importance
    r.type = "reflection"
    r.timestamp = _now()
    r.last_accessed = _now()
    r.source_observation_ids = source_ids or [str(uuid.uuid4()), str(uuid.uuid4())]
    return r


def _make_persona(
    persona_id: str = "pg-test-001",
    reflections: list | None = None,
    tendency_summary: str = "Tends to be careful with purchases.",
) -> MagicMock:
    """Build a minimal mock PersonaRecord."""
    persona = MagicMock()
    persona.persona_id = persona_id
    persona.memory.core.tendency_summary = tendency_summary
    persona.memory.core.identity_statement = "I am a careful shopper."
    persona.memory.core.key_values = ["quality", "trust", "value"]
    persona.memory.core.immutable_constraints.budget_ceiling = None
    persona.memory.core.immutable_constraints.non_negotiables = []
    persona.memory.core.immutable_constraints.absolute_avoidances = []

    # make model_copy return a new mock with updated attributes
    def _model_copy(update=None):
        new_p = _make_persona(persona_id, tendency_summary=tendency_summary)
        if update and "core" in update:
            new_p.memory.core = update["core"]
        return new_p

    persona.memory.model_copy.side_effect = _model_copy
    persona.memory.working.reflections = reflections or []
    return persona


def _make_envelope_with_persona(persona: MagicMock) -> MagicMock:
    env = MagicMock()
    env.personas = [persona]
    return env


# ---------------------------------------------------------------------------
# _is_blocked_content
# ---------------------------------------------------------------------------

class TestIsBlockedContent:
    def test_demographic_keywords_blocked(self):
        assert _is_blocked_content("My age is 34 and I live in Mumbai")
        assert _is_blocked_content("Gender preferences vary")
        assert _is_blocked_content("My income is middle class")
        assert _is_blocked_content("Education matters")

    def test_life_event_keywords_blocked(self):
        assert _is_blocked_content("I was born in Pune")
        assert _is_blocked_content("My childhood was in a joint family")
        assert _is_blocked_content("I grew up watching my grandmother cook")
        assert _is_blocked_content("After I married my husband we moved")

    def test_neutral_content_not_blocked(self):
        assert not _is_blocked_content("I prefer brands that are transparent about ingredients")
        assert not _is_blocked_content("Quality matters more than price for health products")
        assert not _is_blocked_content("I trust peer recommendations over advertising")
        assert not _is_blocked_content("Convenience drives most of my routine purchases")


# ---------------------------------------------------------------------------
# _cluster_reflections
# ---------------------------------------------------------------------------

class TestClusterReflections:
    def test_single_reflection_forms_singleton_cluster(self):
        r = _make_reflection("Quality matters for child nutrition")
        clusters = _cluster_reflections([r])
        assert len(clusters) == 1
        assert len(clusters[0]) == 1

    def test_similar_reflections_cluster_together(self):
        r1 = _make_reflection("Quality nutrition products for my child matter most")
        r2 = _make_reflection("Nutrition quality for children drives my decisions")
        r3 = _make_reflection("I always prioritise nutrition quality when choosing child products")
        clusters = _cluster_reflections([r1, r2, r3])
        # All three share 'quality', 'nutrition', 'child' tokens — expect one cluster
        sizes = sorted([len(c) for c in clusters], reverse=True)
        assert sizes[0] >= 2  # at least two should cluster together

    def test_dissimilar_reflections_form_separate_clusters(self):
        r1 = _make_reflection("Price sensitivity drives most impulse purchases I regret")
        r2 = _make_reflection("Pediatrician recommendations outweigh advertising claims")
        clusters = _cluster_reflections([r1, r2])
        # These share no meaningful tokens — expect 2 clusters
        assert len(clusters) == 2

    def test_returns_all_reflections_across_clusters(self):
        refs = [_make_reflection(f"unique reflection content number {i}") for i in range(5)]
        clusters = _cluster_reflections(refs)
        total = sum(len(c) for c in clusters)
        assert total == 5


# ---------------------------------------------------------------------------
# Demographics and life_defining_events never promoted (S17)
# ---------------------------------------------------------------------------

class TestDemographicsNeverPromoted:
    def test_demographic_reflection_is_blocked_before_executor(self):
        """A reflection with demographic keywords must never reach promotion_executor."""
        demographic_ref = _make_reflection(
            "My age and income bracket define my purchase ceiling",
            importance=9,
        )
        # Create 3 identical demographic reflections (cluster of 3 would normally trigger)
        refs = [
            _make_reflection("My age and income bracket define my purchase ceiling", importance=9),
            _make_reflection("My age and income bracket define my purchase ceiling", importance=9),
            _make_reflection("My age and income bracket define my purchase ceiling", importance=9),
        ]
        # Give unique IDs
        for i, r in enumerate(refs):
            r.id = f"demo-ref-{i:03d}"

        persona = _make_persona(reflections=refs)
        env = _make_envelope_with_persona(persona)

        report = run_annual_review(persona, [env])

        # Demographics must be blocked — zero promotions attempted
        assert report.promotions_attempted == 0
        assert report.promotions_succeeded == 0
        # Blocked entries should explain why
        assert any("blocked:content" in b for b in report.promotions_blocked)

    def test_life_defining_event_reflection_is_blocked(self):
        """A reflection about a life event must never be promoted."""
        refs = [
            _make_reflection("My childhood taught me to distrust fancy packaging", importance=9),
            _make_reflection("Childhood memories of my childhood made me trust local brands", importance=9),
            _make_reflection("Childhood brand exposure shapes adult trust deeply", importance=9),
        ]
        for i, r in enumerate(refs):
            r.id = f"life-ref-{i:03d}"

        persona = _make_persona(reflections=refs)
        env = _make_envelope_with_persona(persona)

        report = run_annual_review(persona, [env])
        assert report.promotions_attempted == 0


# ---------------------------------------------------------------------------
# Legitimate high-importance cluster CAN promote
# ---------------------------------------------------------------------------

class TestLegitimatePromotion:
    def test_high_importance_cluster_attempts_promotion(self):
        """A cluster of 3+ reflections with importance=9 and neutral content
        must have promotions_attempted > 0."""
        content = "Transparency in ingredient sourcing drives trust for health products"
        refs = [
            _make_reflection(content, importance=9),
            _make_reflection("Trust requires transparency about health product ingredients", importance=9),
            _make_reflection("Health product transparency is essential for my trust decisions", importance=9),
        ]
        for i, r in enumerate(refs):
            r.id = f"legit-ref-{i:03d}"

        persona = _make_persona(reflections=refs)
        env = _make_envelope_with_persona(persona)

        report = run_annual_review(persona, [env])
        assert report.reflections_reviewed >= 3
        # The cluster has >= 3 members, all importance=9 — must attempt promotion
        assert report.promotions_attempted >= 1

    def test_importance_8_blocked_by_gate(self):
        """Reflections with importance=8 must be collected (>= 8) but blocked
        by the promotion gate (requires >= 9). None should be attempted."""
        content = "Transparency in health product sourcing matters for decisions"
        refs = [
            _make_reflection(content, importance=8),
            _make_reflection("Sourcing transparency for health products matters", importance=8),
            _make_reflection("Health sourcing transparency drives product trust", importance=8),
        ]
        for i, r in enumerate(refs):
            r.id = f"imp8-ref-{i:03d}"

        persona = _make_persona(reflections=refs)
        env = _make_envelope_with_persona(persona)

        report = run_annual_review(persona, [env])
        # Reviewed (importance >= 8), but not attempted (gate requires >= 9)
        assert report.reflections_reviewed >= 3
        assert report.promotions_attempted == 0
        assert any("gate:importance" in b for b in report.promotions_blocked)


# ---------------------------------------------------------------------------
# AgingReport accuracy
# ---------------------------------------------------------------------------

class TestAgingReportAccuracy:
    def test_report_counts_reviewed_correctly(self):
        """reflections_reviewed counts safe reflections (non-blocked) with importance >= 8."""
        safe_refs = [
            _make_reflection("Trust matters for supplement choices", importance=8),
            _make_reflection("Peer reviews drive supplement decisions", importance=9),
        ]
        blocked_refs = [
            _make_reflection("My income constrains nutrition spend", importance=9),
        ]
        all_refs = safe_refs + blocked_refs
        for i, r in enumerate(all_refs):
            r.id = f"count-ref-{i:03d}"

        persona = _make_persona(reflections=all_refs)
        env = _make_envelope_with_persona(persona)

        report = run_annual_review(persona, [env])
        # 2 safe reflections with importance >= 8
        assert report.reflections_reviewed == 2

    def test_report_persona_id_matches(self):
        persona = _make_persona(persona_id="pg-aging-001")
        report = run_annual_review(persona, [])
        assert report.persona_id == "pg-aging-001"

    def test_empty_history_returns_zero_review(self):
        persona = _make_persona()
        report = run_annual_review(persona, [])
        assert report.reflections_reviewed == 0
        assert report.promotions_attempted == 0
        assert report.promotions_succeeded == 0

    def test_summary_string_contains_key_fields(self):
        report = AgingReport(
            persona_id="pg-test-001",
            reflections_reviewed=10,
            promotions_attempted=3,
            promotions_succeeded=2,
        )
        s = report.summary()
        assert "pg-test-001" in s
        assert "reviewed=10" in s
        assert "attempted=3" in s
        assert "succeeded=2" in s
