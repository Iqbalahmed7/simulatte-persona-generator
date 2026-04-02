"""tests/test_grounding_integration.py — Sprint 9 Grounding Integration Tests.

End-to-end integration tests for the grounded cohort assembly flow.
Tests call assemble_cohort() with domain_data and validate the full pipeline:
  raw texts → signals → features → clusters → grounded tendencies → CohortEnvelope.

Dependencies:
- src/cohort/assembler.py must have domain_data parameter (Codex Sprint 9 change)
- src/grounding/pipeline.py (Sprint 8, already exists)
- tests/fixtures/synthetic_persona.py (already exists)

All tests run without --integration flag. No LLM calls.

Note on cohort diversity helpers
---------------------------------
assemble_cohort() runs G6 (distribution), G7 (distinctiveness), and G8 (type
coverage) gates before building the envelope.  make_synthetic_persona() always
returns the same "Priya Mehta" persona (Mumbai, age 34, middle income,
social/peer archetype), so a raw list of clones fails all three gates.

The helpers below produce a 5-persona cohort that passes all three gates:
- G6: 5 distinct cities, 5 distinct age brackets, 4 distinct income brackets.
- G7: maximally varied 8 anchor attributes → mean cosine distance > 0.35.
- G8: 5 personas spanning 4+ distinct persona types (Social Validator, Loyalist,
      Aspirant, Anxious Optimizer, Pragmatist).
"""

from __future__ import annotations

import uuid

from tests.fixtures.synthetic_persona import make_synthetic_persona
from src.schema.persona import Attribute, PersonaRecord


# ---------------------------------------------------------------------------
# Low-level persona mutation helpers
# ---------------------------------------------------------------------------

def _clone(persona: PersonaRecord, persona_id: str) -> PersonaRecord:
    return persona.model_copy(update={"persona_id": persona_id})


def _set_city(persona: PersonaRecord, city: str) -> PersonaRecord:
    new_loc = persona.demographic_anchor.location.model_copy(update={"city": city})
    new_anc = persona.demographic_anchor.model_copy(update={"location": new_loc})
    return persona.model_copy(update={"demographic_anchor": new_anc})


def _set_age(persona: PersonaRecord, age: int) -> PersonaRecord:
    new_anc = persona.demographic_anchor.model_copy(update={"age": age})
    return persona.model_copy(update={"demographic_anchor": new_anc})


def _set_income(persona: PersonaRecord, bracket: str) -> PersonaRecord:
    new_hh = persona.demographic_anchor.household.model_copy(
        update={"income_bracket": bracket}
    )
    new_anc = persona.demographic_anchor.model_copy(update={"household": new_hh})
    return persona.model_copy(update={"demographic_anchor": new_anc})


def _set_decision_style(persona: PersonaRecord, style: str) -> PersonaRecord:
    new_ins = persona.derived_insights.model_copy(update={"decision_style": style})
    return persona.model_copy(update={"derived_insights": new_ins})


def _set_trust_anchor(persona: PersonaRecord, anchor: str) -> PersonaRecord:
    new_ins = persona.derived_insights.model_copy(update={"trust_anchor": anchor})
    return persona.model_copy(update={"derived_insights": new_ins})


def _set_switching_band(persona: PersonaRecord, band: str) -> PersonaRecord:
    new_sp = persona.behavioural_tendencies.switching_propensity.model_copy(
        update={"band": band}
    )
    new_bt = persona.behavioural_tendencies.model_copy(
        update={"switching_propensity": new_sp}
    )
    return persona.model_copy(update={"behavioural_tendencies": new_bt})


def _set_continuous_attr(
    persona: PersonaRecord, category: str, name: str, value: float
) -> PersonaRecord:
    """Override a continuous attribute value in the given category."""
    existing = persona.attributes[category][name]
    new_attr = existing.model_copy(update={"value": value})
    new_cat = dict(persona.attributes[category])
    new_cat[name] = new_attr
    new_attrs = dict(persona.attributes)
    new_attrs[category] = new_cat
    return persona.model_copy(update={"attributes": new_attrs})


def _set_categorical_attr(
    persona: PersonaRecord, category: str, name: str, value: str
) -> PersonaRecord:
    """Override a categorical attribute value in the given category."""
    cat = dict(persona.attributes.get(category, {}))
    existing = cat.get(name)
    if existing is not None:
        cat[name] = existing.model_copy(update={"value": value})
    else:
        cat[name] = Attribute(
            value=value, type="categorical", label=name.replace("_", " "), source="anchored"
        )
    new_attrs = dict(persona.attributes)
    new_attrs[category] = cat
    return persona.model_copy(update={"attributes": new_attrs})


def _add_anchor_attr(
    persona: PersonaRecord,
    category: str,
    name: str,
    value,
    attr_type: str = "continuous",
) -> PersonaRecord:
    """Add or override an anchor attribute that may not exist in the base fixture."""
    cat = dict(persona.attributes.get(category, {}))
    cat[name] = Attribute(
        value=value,
        type=attr_type,
        label=name.replace("_", " "),
        source="anchored",
    )
    new_attrs = dict(persona.attributes)
    new_attrs[category] = cat
    return persona.model_copy(update={"attributes": new_attrs})


# ---------------------------------------------------------------------------
# Per-archetype persona builders
# All 8 G7 anchor attributes are explicitly set for maximum cosine divergence.
# Types are designed to satisfy G8 scoring rules.
# ---------------------------------------------------------------------------

def _make_social_validator(pid: str, city: str, age: int, income: str) -> PersonaRecord:
    """
    Social Validator: trust_anchor=peer, decision_style=social, social_proof_bias>0.65.
    G7 anchor profile: analytical/expert/low-constraint/career/price/high-social/quality-vs-budget
    """
    p = make_synthetic_persona()
    p = _clone(p, pid)
    p = _set_city(p, city)
    p = _set_age(p, age)
    p = _set_income(p, income)
    p = _set_decision_style(p, "social")
    p = _set_trust_anchor(p, "peer")
    # G7 anchor attrs — maximally spread
    p = _add_anchor_attr(p, "psychology", "personality_type", "social", "categorical")
    p = _set_continuous_attr(p, "psychology", "risk_tolerance", 0.25)
    p = _add_anchor_attr(p, "social", "trust_orientation_primary", "peer", "categorical")
    p = _add_anchor_attr(p, "psychology", "economic_constraint_level", 0.80, "continuous")
    p = _set_categorical_attr(p, "identity", "life_stage_priority", "family")
    p = _set_categorical_attr(p, "values", "primary_value_driver", "price")
    p = _add_anchor_attr(p, "social", "social_orientation", 0.90, "continuous")
    p = _set_categorical_attr(p, "identity", "tension_seed", "quality_vs_budget")
    return p


def _make_loyalist(pid: str, city: str, age: int, income: str) -> PersonaRecord:
    """
    Loyalist: switching=low, decision_style=habitual, brand_loyalty>0.75.
    G7 anchor profile: habitual/brand/mid-constraint/legacy/brand/low-social/loyalty-vs-curiosity
    """
    p = make_synthetic_persona()
    p = _clone(p, pid)
    p = _set_city(p, city)
    p = _set_age(p, age)
    p = _set_income(p, income)
    p = _set_decision_style(p, "habitual")
    p = _set_trust_anchor(p, "authority")
    p = _set_switching_band(p, "low")
    p = _set_continuous_attr(p, "values", "brand_loyalty", 0.82)
    # G7 anchor attrs
    p = _add_anchor_attr(p, "psychology", "personality_type", "habitual", "categorical")
    p = _set_continuous_attr(p, "psychology", "risk_tolerance", 0.65)
    p = _add_anchor_attr(p, "social", "trust_orientation_primary", "brand", "categorical")
    p = _add_anchor_attr(p, "psychology", "economic_constraint_level", 0.20, "continuous")
    p = _set_categorical_attr(p, "identity", "life_stage_priority", "legacy")
    p = _set_categorical_attr(p, "values", "primary_value_driver", "brand")
    p = _add_anchor_attr(p, "social", "social_orientation", 0.15, "continuous")
    p = _set_categorical_attr(p, "identity", "tension_seed", "loyalty_vs_curiosity")
    return p


def _make_aspirant(pid: str, city: str, age: int, income: str) -> PersonaRecord:
    """
    Aspirant: tension_seed=aspiration_vs_constraint, primary_value_driver=status,
              economic_constraint_level>0.6.
    G7 anchor profile: spontaneous/community/high-constraint/personal_growth/status/mid-social/aspiration_vs_constraint
    """
    p = make_synthetic_persona()
    p = _clone(p, pid)
    p = _set_city(p, city)
    p = _set_age(p, age)
    p = _set_income(p, income)
    p = _set_decision_style(p, "spontaneous")
    p = _set_trust_anchor(p, "community")
    p = _set_switching_band(p, "medium")
    # G7 anchor attrs
    p = _add_anchor_attr(p, "psychology", "personality_type", "spontaneous", "categorical")
    p = _set_continuous_attr(p, "psychology", "risk_tolerance", 0.70)
    p = _add_anchor_attr(p, "social", "trust_orientation_primary", "community", "categorical")
    p = _add_anchor_attr(p, "psychology", "economic_constraint_level", 0.75, "continuous")
    p = _set_categorical_attr(p, "identity", "life_stage_priority", "personal_growth")
    p = _set_categorical_attr(p, "values", "primary_value_driver", "status")
    p = _add_anchor_attr(p, "social", "social_orientation", 0.50, "continuous")
    p = _set_categorical_attr(p, "identity", "tension_seed", "aspiration_vs_constraint")
    return p


def _make_anxious_optimizer(pid: str, city: str, age: int, income: str) -> PersonaRecord:
    """
    Anxious Optimizer: decision_style=analytical, risk_tolerance<0.3.
    G7 anchor profile: analytical/expert/low-constraint/career/quality/low-social/control_vs_delegation
    """
    p = make_synthetic_persona()
    p = _clone(p, pid)
    p = _set_city(p, city)
    p = _set_age(p, age)
    p = _set_income(p, income)
    p = _set_decision_style(p, "analytical")
    p = _set_trust_anchor(p, "expert")
    p = _set_switching_band(p, "low")
    p = _set_continuous_attr(p, "values", "brand_loyalty", 0.60)
    # G7 anchor attrs
    p = _add_anchor_attr(p, "psychology", "personality_type", "analytical", "categorical")
    p = _set_continuous_attr(p, "psychology", "risk_tolerance", 0.12)
    p = _add_anchor_attr(p, "social", "trust_orientation_primary", "expert", "categorical")
    p = _add_anchor_attr(p, "psychology", "economic_constraint_level", 0.10, "continuous")
    p = _set_categorical_attr(p, "identity", "life_stage_priority", "career")
    p = _set_categorical_attr(p, "values", "primary_value_driver", "quality")
    p = _add_anchor_attr(p, "social", "social_orientation", 0.20, "continuous")
    p = _set_categorical_attr(p, "identity", "tension_seed", "control_vs_delegation")
    return p


def _make_pragmatist(pid: str, city: str, age: int, income: str) -> PersonaRecord:
    """
    Pragmatist: price_sensitivity=high, switching=high, brand_loyalty<0.35.
    G7 anchor profile: analytical/self/mid-constraint/survival/price/mid-social/independence_vs_validation
    """
    p = make_synthetic_persona()
    p = _clone(p, pid)
    p = _set_city(p, city)
    p = _set_age(p, age)
    p = _set_income(p, income)
    p = _set_decision_style(p, "analytical")
    p = _set_trust_anchor(p, "self")
    p = _set_switching_band(p, "high")
    p = _set_continuous_attr(p, "values", "brand_loyalty", 0.20)
    # G7 anchor attrs
    p = _add_anchor_attr(p, "psychology", "personality_type", "analytical", "categorical")
    p = _set_continuous_attr(p, "psychology", "risk_tolerance", 0.45)
    p = _add_anchor_attr(p, "social", "trust_orientation_primary", "self", "categorical")
    p = _add_anchor_attr(p, "psychology", "economic_constraint_level", 0.50, "continuous")
    p = _set_categorical_attr(p, "identity", "life_stage_priority", "survival")
    p = _set_categorical_attr(p, "values", "primary_value_driver", "price")
    p = _add_anchor_attr(p, "social", "social_orientation", 0.40, "continuous")
    p = _set_categorical_attr(p, "identity", "tension_seed", "independence_vs_validation")
    return p


def _make_diverse_cohort() -> list[PersonaRecord]:
    """Return a 5-persona cohort that passes G6, G7, and G8 gates.

    G6 diversity:
      - 5 distinct cities (Mumbai, Delhi, Chennai, Kolkata, Bangalore)
      - 5 distinct age brackets (18-24, 25-34, 35-44, 45-54, 55-64)
      - 4 distinct income brackets

    G7 distinctiveness:
      - All 8 anchor attributes set with maximally varied values
      - Mean cosine distance > 0.35

    G8 type coverage (5 personas requires 4 distinct types):
      - Social Validator, Loyalist, Aspirant, Anxious Optimizer, Pragmatist
    """
    return [
        _make_social_validator("pg-gi-001", "Mumbai",    34, "middle"),
        _make_loyalist(         "pg-gi-002", "Delhi",     52, "upper-middle"),
        _make_aspirant(         "pg-gi-003", "Chennai",   28, "lower-middle"),
        _make_anxious_optimizer("pg-gi-004", "Kolkata",   44, "high"),
        _make_pragmatist(       "pg-gi-005", "Bangalore", 62, "lower-middle"),
    ]


# ---------------------------------------------------------------------------
# Test 1: Full grounded pipeline — CohortEnvelope shape
# ---------------------------------------------------------------------------

def test_full_grounded_cohort_envelope_shape():
    """
    End-to-end: assemble_cohort with domain_data produces a schema-valid
    CohortEnvelope with all grounding fields correctly populated.
    """
    from src.cohort.assembler import assemble_cohort
    from src.schema.cohort import CohortEnvelope

    domain_data = [
        "I switched brands because the price went up dramatically.",
        "My doctor specifically recommended this supplement.",
        "Bought it after reading trusted expert reviews.",
        "Too expensive — rejected and switched to the cheaper alternative.",
        "A friend's recommendation made me try this brand.",
        "The price was too high — I avoided it completely.",
        "Switched from my old brand when quality improved.",
        "Expert certification gave me confidence to buy.",
    ]
    personas = _make_diverse_cohort()
    envelope = assemble_cohort(personas, domain="cpg", domain_data=domain_data)

    # Schema validity — Pydantic would have raised on construction if invalid
    assert isinstance(envelope, CohortEnvelope)
    assert envelope.mode == "grounded"
    assert envelope.domain == "cpg"
    assert len(envelope.personas) == 5


# ---------------------------------------------------------------------------
# Test 2: GroundingSummary fields all populated
# ---------------------------------------------------------------------------

def test_grounded_cohort_grounding_summary_populated():
    """
    GroundingSummary in grounded mode must have:
    - signals_extracted > 0
    - clusters_derived >= 1
    - tendency_source_distribution sums to 1.0
    - distribution keys = {"grounded", "proxy", "estimated"}
    """
    from src.cohort.assembler import assemble_cohort

    domain_data = [
        "Rejected this product — far too expensive for what it offers.",
        "My friend switched and convinced me to try it.",
        "Expert-certified — I bought it with confidence.",
        "Switched brands after price doubled — couldn't afford it.",
        "Doctor recommended this supplement for my condition.",
    ] * 3  # 15 texts

    personas = _make_diverse_cohort()
    envelope = assemble_cohort(personas, domain="cpg", domain_data=domain_data)
    gs = envelope.grounding_summary

    assert gs.domain_data_signals_extracted > 0
    assert gs.clusters_derived >= 1
    total = sum(gs.tendency_source_distribution.values())
    assert abs(total - 1.0) < 1e-6
    assert set(gs.tendency_source_distribution.keys()) == {"grounded", "proxy", "estimated"}


# ---------------------------------------------------------------------------
# Test 3: TaxonomyMeta.domain_data_used set correctly
# ---------------------------------------------------------------------------

def test_taxonomy_meta_domain_data_used():
    """
    domain_data_used should be True when domain_data provided, False otherwise.
    """
    from src.cohort.assembler import assemble_cohort

    domain_data = ["I bought this after a price comparison.", "Expert review convinced me."]

    # With domain_data
    envelope_grounded = assemble_cohort(
        _make_diverse_cohort(), domain="cpg", domain_data=domain_data
    )
    assert envelope_grounded.taxonomy_used.domain_data_used is True

    # Without domain_data
    envelope_proxy = assemble_cohort(_make_diverse_cohort(), domain="cpg")
    assert envelope_proxy.taxonomy_used.domain_data_used is False


# ---------------------------------------------------------------------------
# Test 4: Grounded source proportion is > 0 after grounding
# ---------------------------------------------------------------------------

def test_grounded_source_proportion_positive():
    """
    After running with domain_data, the 'grounded' proportion in
    tendency_source_distribution should be > 0.
    """
    from src.cohort.assembler import assemble_cohort

    domain_data = [
        f"Product {i} — too expensive, switched to a cheaper alternative." for i in range(10)
    ] + [
        f"Expert review {i} convinced me to buy this product." for i in range(10)
    ]

    personas = _make_diverse_cohort()
    envelope = assemble_cohort(personas, domain="cpg", domain_data=domain_data)
    grounded_frac = envelope.grounding_summary.tendency_source_distribution["grounded"]
    assert grounded_frac > 0.0, f"Expected grounded > 0, got {grounded_frac}"


# ---------------------------------------------------------------------------
# Test 5: Proxy cohort (no domain_data) → signals_extracted = 0, clusters_derived = 0
# ---------------------------------------------------------------------------

def test_proxy_cohort_zeros_in_grounding_summary():
    """
    Without domain_data, grounding summary has:
    - domain_data_signals_extracted == 0
    - clusters_derived == 0
    - grounded proportion == 0.0
    """
    from src.cohort.assembler import assemble_cohort

    personas = _make_diverse_cohort()
    envelope = assemble_cohort(personas, domain="cpg")
    gs = envelope.grounding_summary

    assert gs.domain_data_signals_extracted == 0
    assert gs.clusters_derived == 0
    assert gs.tendency_source_distribution["grounded"] == 0.0


# ---------------------------------------------------------------------------
# Test 6: Multi-persona grounded cohort — all personas updated
# ---------------------------------------------------------------------------

def test_multi_persona_grounded_cohort():
    """
    With 5 diverse personas and domain_data, all personas should be in the
    envelope with at least one grounded tendency each.
    """
    from src.cohort.assembler import assemble_cohort

    personas = _make_diverse_cohort()
    domain_data = [
        "Switched brands after the price doubled.",
        "My trusted friend recommended this product.",
        "Expert-certified organic — bought with confidence.",
        "Rejected because it was too expensive.",
        "Doctor's recommendation — switched immediately.",
    ] * 4  # 20 texts

    envelope = assemble_cohort(personas, domain="cpg", domain_data=domain_data)

    assert len(envelope.personas) == 5
    for persona in envelope.personas:
        bt = persona.behavioural_tendencies
        sources = {
            bt.price_sensitivity.source,
            bt.trust_orientation.source,
            bt.switching_propensity.source,
        }
        assert "grounded" in sources, (
            f"Persona {persona.persona_id} has no grounded tendency — sources: {sources}"
        )


# ---------------------------------------------------------------------------
# Test 7: Warning accessible via pipeline (below 200 signals)
# ---------------------------------------------------------------------------

def test_grounded_cohort_below_200_still_builds():
    """
    Even with < 200 texts (below the grounding threshold), the cohort
    assembles successfully. The pipeline emits a warning internally,
    but assemble_cohort does not raise.
    """
    from src.cohort.assembler import assemble_cohort

    small_domain_data = [
        "Bought this — price was right.",
        "Switched due to price increase.",
        "Expert recommended it.",
    ]  # Only 3 texts — below 200 threshold

    personas = _make_diverse_cohort()
    # Must not raise
    envelope = assemble_cohort(personas, domain="cpg", domain_data=small_domain_data)
    assert envelope.mode == "grounded"
    assert envelope.grounding_summary.domain_data_signals_extracted > 0


# ---------------------------------------------------------------------------
# Test 8: ICPSpec.domain_data field accessible
# ---------------------------------------------------------------------------

def test_icp_spec_domain_data_field():
    """
    ICPSpec (Sprint 9 Cursor) should now have a domain_data field.
    """
    from src.generation.identity_constructor import ICPSpec
    spec = ICPSpec(
        domain="cpg",
        mode="grounded",
        domain_data=["Too expensive — rejected.", "Friend recommended it."],
    )
    assert hasattr(spec, "domain_data")
    assert spec.domain_data is not None
    assert len(spec.domain_data) == 2
