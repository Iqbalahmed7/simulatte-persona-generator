"""pilots/littlejoys/app_adapter.py

Adapter: load a CohortEnvelope from disk and convert PersonaRecord objects
to the dict format expected by the LittleJoys Streamlit app.

Two public functions:
  load_simulatte_cohort(path) -> list[PersonaRecord]
  persona_to_display_dict(p: PersonaRecord) -> dict
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path bootstrap — allow importing from the project root regardless of cwd
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.persistence.envelope_store import load_envelope  # noqa: E402
from src.schema.persona import PersonaRecord  # noqa: E402


# ---------------------------------------------------------------------------
# City-tier normalisation
# ---------------------------------------------------------------------------

# PersonaRecord stores urban_tier as one of: "metro", "tier2", "tier3", "rural"
# The LJ app uses "Tier1" / "Tier2" / "Tier3" style labels in some places and
# the raw urban_tier string in others.  We surface both so callers can choose.

_URBAN_TIER_TO_LJ: dict[str, str] = {
    "metro": "Tier1",
    "tier2": "Tier2",
    "tier3": "Tier3",
    "rural": "Rural",
}


def _lj_city_tier(urban_tier: str | None) -> str:
    """Convert PersonaRecord UrbanTier to LittleJoys city_tier label."""
    if not urban_tier:
        return "Unknown"
    return _URBAN_TIER_TO_LJ.get(urban_tier.lower(), urban_tier)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_simulatte_cohort(path: str | Path) -> list[PersonaRecord]:
    """Load a CohortEnvelope from *path* and return its list of PersonaRecords.

    Args:
        path: Path to a JSON file saved by ``save_envelope()``.

    Returns:
        ``envelope.personas`` — a list of :class:`~src.schema.persona.PersonaRecord`.

    Raises:
        FileNotFoundError: If *path* does not exist on disk.
        ValueError: If the JSON cannot be parsed as a valid CohortEnvelope.
    """
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Cohort file not found: {path}")
    envelope = load_envelope(resolved)
    return envelope.personas


def persona_to_display_dict(p: PersonaRecord) -> dict[str, Any]:
    """Convert a PersonaRecord to the flat+nested dict the LJ Streamlit app expects.

    Only ``p.persona_id`` and ``p.demographic_anchor`` are treated as
    guaranteed to exist.  Every other field is accessed via ``getattr`` with a
    safe default so that older personas (pre-Sprint 19) never raise.

    Args:
        p: A :class:`~src.schema.persona.PersonaRecord` instance.

    Returns:
        A dict with keys: ``id``, ``name``, ``demographics``, ``parent_traits``,
        ``budget_profile``, and ``simulatte``.
    """
    da = p.demographic_anchor  # DemographicAnchor — always present

    # ------------------------------------------------------------------
    # demographic_anchor sub-objects
    # ------------------------------------------------------------------
    location = getattr(da, "location", None)
    household = getattr(da, "household", None)

    city_name: str | None = getattr(location, "city", None)
    urban_tier: str | None = getattr(location, "urban_tier", None)
    family_structure: str | None = getattr(household, "structure", None)
    income_bracket: str | None = getattr(household, "income_bracket", None)
    employment: str | None = getattr(da, "employment", None)

    # child_ages: not stored in PersonaRecord's DemographicAnchor.  The
    # household.size field gives total household size (not just children), so
    # we cannot reliably derive individual child ages.  We return [] so the LJ
    # app's age-band filters degrade gracefully rather than crashing.
    child_ages: list[int] = []

    # monthly_income: PersonaRecord stores income_bracket (a string label such
    # as "middle", "upper-middle", etc.) rather than a numeric monthly figure.
    # We surface it under the monthly_income key so callers can display it;
    # numeric wtp_inr in the simulatte block is the closest monetary proxy.
    monthly_income: str | None = income_bracket

    # ------------------------------------------------------------------
    # derived_insights
    # ------------------------------------------------------------------
    di = getattr(p, "derived_insights", None)

    trust_anchor: str | None = getattr(di, "trust_anchor", None)
    decision_style: str | None = getattr(di, "decision_style", None)
    # risk_appetite lives on derived_insights in the current schema
    risk_tolerance: str | None = getattr(di, "risk_appetite", None)
    consistency_score: int | None = getattr(di, "consistency_score", None)

    # Sprint 19+ optional fields on derived_insights
    wtp_inr: Any = getattr(di, "wtp_inr", None)
    noise_applied: Any = getattr(di, "noise_applied", None)
    confidence_score: Any = getattr(di, "confidence_score", None)

    # ------------------------------------------------------------------
    # behavioural_tendencies
    # ------------------------------------------------------------------
    bt = getattr(p, "behavioural_tendencies", None)
    ps_obj = getattr(bt, "price_sensitivity", None)
    price_sensitivity: str | None = getattr(ps_obj, "band", None)

    # ------------------------------------------------------------------
    # memory
    # ------------------------------------------------------------------
    memory = getattr(p, "memory", None)
    working = getattr(memory, "working", None)

    observations: list = getattr(working, "observations", []) or []
    reflections: list = getattr(working, "reflections", []) or []

    last_reflection: Any = None
    if reflections:
        last_ref_obj = reflections[-1]
        # Prefer the .content string; fall back to the raw object
        last_reflection = getattr(last_ref_obj, "content", last_ref_obj)

    # ------------------------------------------------------------------
    # Sprint 19+ top-level fields (absent on most existing personas)
    # ------------------------------------------------------------------
    simulation_tier: Any = getattr(p, "simulation_tier", None)
    aging_status: Any = getattr(p, "aging_status", None)

    # ------------------------------------------------------------------
    # Assemble display dict
    # ------------------------------------------------------------------
    return {
        # Top-level identity
        "id": p.persona_id,
        "name": da.name,

        # demographics block — matches LJ app key names
        "demographics": {
            "age": da.age,
            "city_name": city_name,
            "city_tier": _lj_city_tier(urban_tier),
            "family_structure": family_structure if family_structure is not None else "nuclear_family",
            "child_ages": child_ages,
            "monthly_income": monthly_income,
            "employment_status": employment,
        },

        # parent_traits block
        "parent_traits": {
            "trust_anchor": trust_anchor,
            "decision_style": decision_style,
            "risk_tolerance": risk_tolerance,
        },

        # budget_profile block
        "budget_profile": {
            "price_sensitivity": price_sensitivity,
            "wtp_inr": wtp_inr,
        },

        # Simulatte-specific extras (Sprint 23 UI)
        "simulatte": {
            "persona_id": p.persona_id,
            "confidence_score": confidence_score,
            "noise_applied": noise_applied,
            "consistency_score": consistency_score,
            "memory_observations": len(observations),
            "memory_reflections": len(reflections),
            "last_reflection": last_reflection,
            "tier": simulation_tier,
            "aging_status": aging_status,
        },
    }
