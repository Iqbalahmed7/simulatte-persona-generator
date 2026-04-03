"""src/registry/persona_regrounder.py — Domain layer swap utility.

Implements Scenario B and C from PERSONA_REUSE_MODALITIES.md:
- Layer A (permanent identity): preserved exactly as-is
- Layer B (domain expression): behavioural_tendencies sources → "estimated";
  persona.domain updated to new_domain

No LLM calls. Deterministic.
"""
from __future__ import annotations

from src.schema.persona import (
    BehaviouralTendencies,
    PersonaRecord,
    PriceSensitivityBand,
    TendencyBand,
    TrustOrientation,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def reground_for_domain(persona: PersonaRecord, new_domain: str) -> PersonaRecord:
    """Return a new PersonaRecord with domain updated and tendency sources set to 'estimated'.

    What changes:
    - persona.domain = new_domain
    - behavioural_tendencies.price_sensitivity.source = "estimated"
    - behavioural_tendencies.trust_orientation.source = "estimated"
    - behavioural_tendencies.switching_propensity.source = "estimated"

    What is preserved (Layer A — permanent identity):
    - persona_id, generated_at, generator_version, mode
    - demographic_anchor (all fields)
    - life_stories
    - attributes (all domain-specific attributes are left as-is; caller manages if needed)
    - derived_insights
    - narrative
    - decision_bullets
    - memory.core (never modified — core memory accumulation is valuable)
    - memory.working (preserved; caller must reset before new experiment)

    Returns a completely new PersonaRecord object (not mutated in-place).
    No LLM calls.
    """
    new_tendencies = _downgrade_sources(persona.behavioural_tendencies)
    return persona.model_copy(update={
        "domain": new_domain,
        "behavioural_tendencies": new_tendencies,
    })


# ---------------------------------------------------------------------------
# Helper: downgrade tendency sources to "estimated"
# ---------------------------------------------------------------------------

def _downgrade_sources(tendencies: BehaviouralTendencies) -> BehaviouralTendencies:
    """Return a new BehaviouralTendencies with all source fields set to 'estimated'.

    price_sensitivity, trust_orientation, switching_propensity all have source fields.
    objection_profile entries do not have source fields — preserved as-is.
    """
    new_ps = tendencies.price_sensitivity.model_copy(update={"source": "estimated"})
    new_to = tendencies.trust_orientation.model_copy(update={"source": "estimated"})
    new_sp = tendencies.switching_propensity.model_copy(update={"source": "estimated"})
    return tendencies.model_copy(update={
        "price_sensitivity": new_ps,
        "trust_orientation": new_to,
        "switching_propensity": new_sp,
    })
