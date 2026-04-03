"""tests/test_app_adapter.py — Sprint 23: adapter test suite.

Tests for:
  pilots/littlejoys/app_adapter.py — load_simulatte_cohort + persona_to_display_dict
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap — ensure project root is importable regardless of cwd
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pilots.littlejoys.app_adapter import load_simulatte_cohort, persona_to_display_dict  # noqa: E402
from tests.fixtures.synthetic_persona import make_synthetic_persona  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REAL_COHORT_PATH = Path(
    "/Users/admin/Documents/Simulatte Projects/1. LittleJoys/data/population"
    "/simulatte_cohort_final.json"
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def persona():
    """Full, valid PersonaRecord built from the synthetic fixture."""
    return make_synthetic_persona()


@pytest.fixture(scope="module")
def display(persona):
    """persona_to_display_dict result for the synthetic persona."""
    return persona_to_display_dict(persona)


# ---------------------------------------------------------------------------
# Acceptance criterion 1 — top-level keys
# ---------------------------------------------------------------------------


def test_display_dict_top_level_keys(display):
    """persona_to_display_dict returns all six required top-level keys."""
    required = {"id", "name", "demographics", "parent_traits", "budget_profile", "simulatte"}
    assert required <= display.keys(), (
        f"Missing keys: {required - display.keys()}"
    )


# ---------------------------------------------------------------------------
# Acceptance criterion 2 — demographics sub-keys
# ---------------------------------------------------------------------------


def test_demographics_keys(display):
    """demographics dict contains every required key."""
    required = {
        "age",
        "city_name",
        "city_tier",
        "family_structure",
        "child_ages",
        "monthly_income",
        "employment_status",
    }
    assert required <= display["demographics"].keys(), (
        f"Missing demographics keys: {required - display['demographics'].keys()}"
    )


# ---------------------------------------------------------------------------
# Acceptance criterion 3 — parent_traits sub-keys
# ---------------------------------------------------------------------------


def test_parent_traits_keys(display):
    """parent_traits dict contains trust_anchor, decision_style, risk_tolerance."""
    required = {"trust_anchor", "decision_style", "risk_tolerance"}
    assert required <= display["parent_traits"].keys(), (
        f"Missing parent_traits keys: {required - display['parent_traits'].keys()}"
    )


# ---------------------------------------------------------------------------
# Acceptance criterion 4 — budget_profile sub-keys
# ---------------------------------------------------------------------------


def test_budget_profile_keys(display):
    """budget_profile dict contains price_sensitivity and wtp_inr."""
    required = {"price_sensitivity", "wtp_inr"}
    assert required <= display["budget_profile"].keys(), (
        f"Missing budget_profile keys: {required - display['budget_profile'].keys()}"
    )


# ---------------------------------------------------------------------------
# Acceptance criterion 5 — simulatte sub-keys
# ---------------------------------------------------------------------------


def test_simulatte_keys(display):
    """simulatte dict contains persona_id, memory_observations, memory_reflections."""
    required = {"persona_id", "memory_observations", "memory_reflections"}
    assert required <= display["simulatte"].keys(), (
        f"Missing simulatte keys: {required - display['simulatte'].keys()}"
    )


# ---------------------------------------------------------------------------
# Acceptance criterion 6 — missing optional fields do not raise
# ---------------------------------------------------------------------------


def test_missing_optional_fields_do_not_raise(persona):
    """persona_to_display_dict does not raise when optional fields are absent.

    We create a fresh persona via the factory (which does NOT set Sprint-19+
    optional fields such as derived_insights.wtp_inr, simulation_tier, or
    aging_status) and verify the call completes without error.  None values
    are acceptable for optional keys.
    """
    result = persona_to_display_dict(persona)
    # Optional Sprint-19 fields default to None — no KeyError / AttributeError
    assert result["simulatte"]["tier"] is None
    assert result["simulatte"]["aging_status"] is None
    assert result["budget_profile"]["wtp_inr"] is None


# ---------------------------------------------------------------------------
# Acceptance criterion 7 — FileNotFoundError for missing cohort path
# ---------------------------------------------------------------------------


def test_load_cohort_missing_path_raises_file_not_found():
    """load_simulatte_cohort raises FileNotFoundError for a non-existent path."""
    missing = Path("/tmp/this_path_does_not_exist_simulatte_test.json")
    with pytest.raises(FileNotFoundError) as exc_info:
        load_simulatte_cohort(missing)
    assert "not found" in str(exc_info.value).lower(), (
        f"Expected 'not found' in error message, got: {exc_info.value}"
    )


# ---------------------------------------------------------------------------
# Acceptance criteria 8 & 9 & 10 — integration tests against real cohort file
# ---------------------------------------------------------------------------


@pytest.mark.cohort
def test_load_real_cohort_returns_nonempty_list():
    """load_simulatte_cohort against the real cohort JSON returns a non-empty list."""
    personas = load_simulatte_cohort(REAL_COHORT_PATH)
    assert len(personas) > 0, "Expected at least one PersonaRecord in cohort"


@pytest.mark.cohort
def test_round_trip_name_is_nonempty_string():
    """Round-trip: first persona from real cohort → display dict → name is non-empty string."""
    personas = load_simulatte_cohort(REAL_COHORT_PATH)
    d = persona_to_display_dict(personas[0])
    name = d["name"]
    assert isinstance(name, str) and len(name) > 0, (
        f"Expected non-empty string for name, got: {name!r}"
    )


@pytest.mark.cohort
def test_city_tier_normalisation_is_string():
    """city_tier for every persona in the real cohort is a non-None string."""
    personas = load_simulatte_cohort(REAL_COHORT_PATH)
    for p in personas:
        d = persona_to_display_dict(p)
        city_tier = d["demographics"]["city_tier"]
        assert isinstance(city_tier, str), (
            f"city_tier is not a string for persona {p.persona_id!r}: {city_tier!r}"
        )


# ---------------------------------------------------------------------------
# Extra unit-level sanity checks (not in acceptance criteria, but cheap)
# ---------------------------------------------------------------------------


def test_display_id_matches_persona_id(persona, display):
    """id in display dict matches persona.persona_id."""
    assert display["id"] == persona.persona_id


def test_simulatte_persona_id_matches(persona, display):
    """simulatte.persona_id duplicates the top-level id."""
    assert display["simulatte"]["persona_id"] == display["id"]


def test_demographics_age_matches(persona, display):
    """demographics.age matches demographic_anchor.age."""
    assert display["demographics"]["age"] == persona.demographic_anchor.age


def test_demographics_child_ages_is_list(display):
    """demographics.child_ages is always a list (may be empty)."""
    assert isinstance(display["demographics"]["child_ages"], list)


def test_city_tier_metro_normalises_to_tier1(persona, display):
    """urban_tier='metro' on the synthetic persona normalises to 'Tier1'."""
    # synthetic persona has urban_tier="metro"
    assert display["demographics"]["city_tier"] == "Tier1"


def test_simulatte_memory_counts_are_ints(display):
    """memory_observations and memory_reflections are non-negative ints."""
    assert isinstance(display["simulatte"]["memory_observations"], int)
    assert isinstance(display["simulatte"]["memory_reflections"], int)
    assert display["simulatte"]["memory_observations"] >= 0
    assert display["simulatte"]["memory_reflections"] >= 0
