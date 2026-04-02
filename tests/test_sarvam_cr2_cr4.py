"""tests/test_sarvam_cr2_cr4.py — CR2 and CR4 validator tests.

Sprint 15 — Sarvam Integration Validation.
6 tests covering CR2 (anti-stereotypicality audit) and CR4 (persona fidelity check).

No LLM calls. No --integration flag required.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# CR2 tests
# ---------------------------------------------------------------------------

def test_cr2_clean_narrative_passes():
    """Narrative with no prohibited patterns passes CR2."""
    from src.sarvam.cr2_validator import run_cr2_check

    first = (
        "I am Priya Mehta, a working mother in Mumbai. "
        "I compare prices carefully before every purchase and rely on my peer network."
    )
    third = (
        "Priya Mehta is a 34-year-old professional in Mumbai who evaluates "
        "every purchase through the lens of family welfare and budget discipline."
    )

    result = run_cr2_check(
        persona_id="test-cr2-001",
        enriched_narrative_first=first,
        enriched_narrative_third=third,
    )

    assert result.passed is True
    assert result.hard_violations == []
    assert result.persona_id == "test-cr2-001"


def test_cr2_detects_jugaad():
    """Narrative containing 'jugaad' fails CR2."""
    from src.sarvam.cr2_validator import run_cr2_check

    first = (
        "I rely on jugaad to solve everyday household problems and save money."
    )
    third = (
        "Priya applies jugaad thinking to stretch her household budget further."
    )

    result = run_cr2_check(
        persona_id="test-cr2-002",
        enriched_narrative_first=first,
        enriched_narrative_third=third,
    )

    assert result.passed is False
    assert "jugaad" in result.hard_violations


def test_cr2_joint_family_ok_for_joint_household():
    """'joint family' is allowed when household.structure == 'joint'."""
    from src.sarvam.cr2_validator import run_cr2_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    # Build a persona with joint household structure
    persona = make_synthetic_persona()
    joint_household = persona.demographic_anchor.household.model_copy(
        update={"structure": "joint"}
    )
    joint_anchor = persona.demographic_anchor.model_copy(
        update={"household": joint_household}
    )
    joint_persona = persona.model_copy(update={"demographic_anchor": joint_anchor})

    first = "Living in a joint family home, I share decisions with my in-laws and husband."
    third = "Priya lives in a joint family setup in Mumbai where decisions are collective."

    result = run_cr2_check(
        persona_id="test-cr2-003",
        enriched_narrative_first=first,
        enriched_narrative_third=third,
        persona_record=joint_persona,
    )

    # "joint family" is in the text but should be excused by joint household structure
    assert result.passed is True
    assert "joint family" not in result.hard_violations


# ---------------------------------------------------------------------------
# CR4 tests
# ---------------------------------------------------------------------------

def test_cr4_name_preserved():
    """CR4 passes when persona name appears in enriched narrative."""
    from src.sarvam.cr4_validator import run_cr4_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    original = (
        "Priya Mehta is a 34-year-old professional in Mumbai focused on family welfare."
    )
    enriched = (
        "Priya Mehta navigates the vibrant local markets of Mumbai, balancing her "
        "family's needs with a disciplined household budget."
    )

    result = run_cr4_check(
        persona_id="test-cr4-001",
        original_narrative=original,
        enriched_narrative=enriched,
        persona_record=persona,
    )

    assert result.passed is True
    assert result.missing_facts == []


def test_cr4_missing_name_fails():
    """CR4 fails when persona name is absent from enriched narrative."""
    from src.sarvam.cr4_validator import run_cr4_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    original = (
        "Priya Mehta is a 34-year-old professional in Mumbai focused on family welfare."
    )
    # Enriched narrative accidentally drops the persona's name
    enriched = (
        "She navigates local markets in Mumbai, balancing family needs with budget discipline."
    )

    result = run_cr4_check(
        persona_id="test-cr4-002",
        original_narrative=original,
        enriched_narrative=enriched,
        persona_record=persona,
    )

    assert result.passed is False
    assert any("Priya" in fact for fact in result.missing_facts)


def test_cr4_city_check():
    """CR4 checks that city appears in enriched narrative."""
    from src.sarvam.cr4_validator import run_cr4_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    original = (
        "Priya Mehta is a 34-year-old professional in Mumbai focused on family welfare."
    )
    # Enriched narrative omits the city
    enriched = (
        "Priya Mehta manages her household budget carefully, relying on peer recommendations "
        "before any non-routine purchase."
    )

    result = run_cr4_check(
        persona_id="test-cr4-003",
        original_narrative=original,
        enriched_narrative=enriched,
        persona_record=persona,
    )

    assert result.passed is False
    assert any("Mumbai" in fact for fact in result.missing_facts)
