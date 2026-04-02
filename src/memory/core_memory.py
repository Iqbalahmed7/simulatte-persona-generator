"""src/memory/core_memory.py — Authoritative CoreMemory assembly.

Sprint 3 — OpenCode (Core Memory + Seed Memory Engineer)

Replaces the _assemble_core_memory() stub in identity_constructor.py.
Called from Step 6 of IdentityConstructor.build():

    from src.memory.core_memory import assemble_core_memory
    core_memory = assemble_core_memory(persona_record)

Zero LLM calls. All derivations are deterministic.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from src.schema.persona import (
    CoreMemory,
    ImmutableConstraints,
    LifeDefiningEvent,
    PersonaRecord,
    RelationshipMap,
)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def assemble_core_memory(persona: PersonaRecord) -> CoreMemory:
    """Assemble CoreMemory from a validated PersonaRecord.

    All fields are derived deterministically — no LLM calls.

    Called once during persona creation. The result is stored in
    PersonaRecord.memory.core and is immutable thereafter.
    """
    identity_statement = _derive_identity_statement(persona)
    key_values = _derive_key_values(persona)
    life_defining_events = _derive_life_defining_events(persona)
    relationship_map = _derive_relationship_map(persona)
    immutable_constraints = _derive_immutable_constraints(persona)
    tendency_summary: str = persona.behavioural_tendencies.reasoning_prompt

    return CoreMemory(
        identity_statement=identity_statement,
        key_values=key_values,
        life_defining_events=life_defining_events,
        relationship_map=relationship_map,
        immutable_constraints=immutable_constraints,
        tendency_summary=tendency_summary,
    )


# ---------------------------------------------------------------------------
# identity_statement
# ---------------------------------------------------------------------------


def _derive_identity_statement(persona: PersonaRecord) -> str:
    """First 25 words of persona.narrative.first_person.

    - If fewer than 25 words, use the full text.
    - Strip trailing punctuation (,;:—) and ensure it ends with a period.
    """
    words = persona.narrative.first_person.split()
    truncated = " ".join(words[:25])
    # Strip trailing non-sentence punctuation but keep sentence-ending ones.
    truncated = truncated.rstrip(",;:—-").strip()
    # Ensure it ends with a period (not !, ?, or already .).
    if truncated and truncated[-1] not in (".", "!", "?"):
        truncated += "."
    return truncated


# ---------------------------------------------------------------------------
# key_values
# ---------------------------------------------------------------------------

# Human-readable labels for each primary_value_driver option (anchor attr).
_VALUE_DRIVER_LABELS: dict[str, str] = {
    "price": "Quality over price",
    "quality": "Quality over price",
    "brand": "Brand trust and reputation",
    "convenience": "Convenience first",
    "relationships": "Relationships over transactions",
    "status": "Status and social signalling",
    # Fallback for any future taxonomy additions
}

# Tension seed → value statement (maps aspiration_vs_constraint → readable phrase).
_TENSION_SEED_VALUE_STATEMENTS: dict[str, str] = {
    "aspiration_vs_constraint": "Driven by aspiration despite real constraints",
    "independence_vs_validation": "Values independence while navigating need for approval",
    "quality_vs_budget": "Seeks quality outcomes within budget limits",
    "loyalty_vs_curiosity": "Balances brand loyalty against curiosity for new options",
    "control_vs_delegation": "Prefers control but open to delegating when trust is established",
}


def _derive_key_values(persona: PersonaRecord) -> list[str]:
    """Build a 3–5 item key_values list.

    Assembly order:
    1. Human-readable label of primary_value_driver anchor.
    2. Value statement derived from tension_seed.
    3–4. Up to 3 more from top-scoring values category attributes
         (highest absolute deviation from 0.5 among continuous attrs).
    Clamped to 5 maximum, guaranteed minimum 3.
    """
    seen: set[str] = set()
    result: list[str] = []

    def _add(item: str) -> None:
        if item not in seen and len(result) < 5:
            seen.add(item)
            result.append(item)

    # 1. Primary value driver label.
    values_cat: dict[str, Any] = persona.attributes.get("values", {})
    pvd_attr = values_cat.get("primary_value_driver")
    if pvd_attr is not None:
        pvd_label = _VALUE_DRIVER_LABELS.get(
            str(pvd_attr.value),
            str(pvd_attr.value).replace("_", " ").title(),
        )
    else:
        pvd_label = _VALUE_DRIVER_LABELS.get(
            str(persona.derived_insights.primary_value_orientation),
            str(persona.derived_insights.primary_value_orientation).replace("_", " ").title(),
        )
    _add(pvd_label)

    # 2. Tension seed → value statement.
    identity_cat: dict[str, Any] = persona.attributes.get("identity", {})
    tension_seed_attr = identity_cat.get("tension_seed")
    if tension_seed_attr is not None:
        tension_key = str(tension_seed_attr.value)
        tension_stmt = _TENSION_SEED_VALUE_STATEMENTS.get(
            tension_key,
            tension_key.replace("_", " ").title(),
        )
        _add(tension_stmt)

    # 3–4. Top continuous attributes from values category by |value - 0.5| deviation.
    continuous_values: list[tuple[str, Any]] = [
        (name, attr)
        for name, attr in values_cat.items()
        if name != "primary_value_driver"
        and hasattr(attr, "type")
        and attr.type == "continuous"
        and isinstance(attr.value, (int, float))
    ]
    # Sort descending by deviation from 0.5.
    continuous_values.sort(key=lambda t: abs(float(t[1].value) - 0.5), reverse=True)

    for name, attr in continuous_values:
        if len(result) >= 5:
            break
        label = attr.label if attr.label else name.replace("_", " ").replace("-", " ").title()
        _add(label)

    # Pad to 3 with fallbacks from derived_insights if needed.
    fallbacks = [
        str(persona.derived_insights.trust_anchor).replace("_", " ").title(),
        str(persona.derived_insights.risk_appetite).replace("_", " ").title() + " risk tolerance",
        str(persona.derived_insights.decision_style).replace("_", " ").title() + " decision-maker",
    ]
    for fb in fallbacks:
        if len(result) >= 3:
            break
        _add(fb)

    return result[:5]


# ---------------------------------------------------------------------------
# life_defining_events
# ---------------------------------------------------------------------------


def _derive_life_defining_events(persona: PersonaRecord) -> list[LifeDefiningEvent]:
    """Convert each LifeStory in persona.life_stories to a LifeDefiningEvent.

    age_when parsing:
    - "age 24" / "at 24" / "24 years old" / bare "24" → 24
    - 4-digit year (1900–2099) → year - (current_year - persona_age)
    - Fallback: 0
    """
    current_age: int = persona.demographic_anchor.age

    events: list[LifeDefiningEvent] = []
    for story in persona.life_stories:
        age_when = _parse_age_from_when(story.when, current_age)
        events.append(
            LifeDefiningEvent(
                age_when=age_when,
                event=story.event,
                lasting_impact=story.lasting_impact,
            )
        )
    return events


def _parse_age_from_when(when_str: str, current_age: int) -> int:
    """Parse an integer age from a free-form 'when' string.

    Accepted patterns (case-insensitive):
      "age 24", "at 24", "24 years old", bare integer "24"
    4-digit year (1900–2099):
      year - birth_year → approximate age at event.
    Fallback: 0 (per brief spec).
    """
    if not when_str:
        return 0

    s = when_str.strip().lower()

    # Try 4-digit year first (before 1–2 digit match to avoid false positives).
    m_year = re.search(r"\b(1[89]\d{2}|20\d{2})\b", s)
    if m_year:
        year = int(m_year.group(1))
        birth_year = datetime.now(tz=timezone.utc).year - current_age
        age_at_event = year - birth_year
        if 1 <= age_at_event <= 120:
            return age_at_event

    # 1–2 digit age from common patterns.
    m = re.search(r"\b(\d{1,3})\b", s)
    if m:
        candidate = int(m.group(1))
        if 1 <= candidate <= 120:
            return candidate

    return 0


# ---------------------------------------------------------------------------
# relationship_map
# ---------------------------------------------------------------------------

# Map household structure + trust_orientation_primary → primary_decision_partner.
_HOUSEHOLD_FAMILY_TRUST_MAP: dict[str, str] = {
    "joint": "Spouse/partner",
    "nuclear": "Spouse/partner",
    "single-parent": "Children / close family",
    "couple-no-kids": "Partner",
    "other": "Self",
}

_TRUST_ANCHOR_PARTNER_MAP: dict[str, str] = {
    "self": "Self",
    "peer": "Close friends",
    "authority": "Trusted expert/advisor",
    "family": "Spouse/partner",
}

# Trust weight field names → generic influencer labels.
_TRUST_WEIGHT_LABELS: dict[str, str] = {
    "expert": "Expert reviews",
    "peer": "Peer recommendations",
    "brand": "Trusted brand signals",
    "ad": "Advertising and promotions",
    "community": "Social community",
    "influencer": "Social influencers",
}


def _derive_relationship_map(persona: PersonaRecord) -> RelationshipMap:
    """Assemble RelationshipMap from household + trust orientation data.

    primary_decision_partner:
      - Joint/nuclear household + family trust → "Spouse/partner"
      - Single-parent → "Children / close family"
      - Couple-no-kids → "Partner"
      - Self trust → "Self"
      - Peer trust → "Close friends"
      - Authority trust → "Trusted expert/advisor"

    key_influencers:
      Top 2 non-self trust weight sources (by weight value), labeled generically.

    trust_network:
      Top 2–3 sources with weight > 0.5. If none exceed 0.5,
      include the single highest-weight source as fallback.
    """
    structure = persona.demographic_anchor.household.structure

    # Determine trust anchor from attributes if available, else from derived_insights.
    social_cat: dict[str, Any] = persona.attributes.get("social", {})
    trust_primary_attr = social_cat.get("trust_orientation_primary")
    if trust_primary_attr is not None:
        trust_primary = str(trust_primary_attr.value)
    else:
        trust_primary = str(persona.derived_insights.trust_anchor)

    # primary_decision_partner: household structure takes precedence for
    # joint/nuclear/single-parent/couple-no-kids; trust anchor used for "other".
    if structure in ("joint", "nuclear"):
        if trust_primary == "family":
            primary_decision_partner = "Spouse/partner"
        elif trust_primary == "self":
            primary_decision_partner = "Self"
        elif trust_primary == "peer":
            primary_decision_partner = "Close friends"
        elif trust_primary == "authority":
            primary_decision_partner = "Trusted expert/advisor"
        else:
            primary_decision_partner = "Spouse/partner"
    elif structure == "single-parent":
        primary_decision_partner = "Children / close family"
    elif structure == "couple-no-kids":
        primary_decision_partner = "Partner"
    else:
        # "other" — use trust anchor.
        primary_decision_partner = _TRUST_ANCHOR_PARTNER_MAP.get(trust_primary, "Self")

    # Build sorted trust weight pairs.
    weights = persona.behavioural_tendencies.trust_orientation.weights
    weight_pairs: list[tuple[str, float]] = [
        ("expert", weights.expert),
        ("peer", weights.peer),
        ("brand", weights.brand),
        ("ad", weights.ad),
        ("community", weights.community),
        ("influencer", weights.influencer),
    ]
    weight_pairs_sorted = sorted(weight_pairs, key=lambda t: t[1], reverse=True)

    # key_influencers: top 2 non-self sources by weight.
    # "self" has no weight field — all 6 sources are external, so take top 2.
    key_influencers: list[str] = [
        _TRUST_WEIGHT_LABELS[name]
        for name, _ in weight_pairs_sorted[:2]
    ]

    # trust_network: sources with weight > 0.5; fallback to top source if empty.
    trust_network: list[str] = [
        _TRUST_WEIGHT_LABELS[name]
        for name, w in weight_pairs_sorted
        if w > 0.5
    ]
    # Also factor in peer_influence_strength and online_community_trust from
    # social attributes to populate trust_network generically.
    peer_influence = social_cat.get("peer_influence_strength")
    online_community = social_cat.get("online_community_trust")

    if peer_influence is not None and isinstance(peer_influence.value, (int, float)):
        if float(peer_influence.value) > 0.5 and "Peer recommendations" not in trust_network:
            trust_network.append("Peer recommendations")
    if online_community is not None and isinstance(online_community.value, (int, float)):
        if float(online_community.value) > 0.5 and "Online communities" not in trust_network:
            trust_network.append("Online communities")

    # Fallback: at least 1 entry.
    if not trust_network:
        trust_network = [_TRUST_WEIGHT_LABELS[weight_pairs_sorted[0][0]]]

    # Clamp trust_network to 3 entries max.
    trust_network = trust_network[:3]

    # Ensure key_influencers has at least 2 entries (pad with trust_network if needed).
    while len(key_influencers) < 2 and trust_network:
        candidate = trust_network[0]
        if candidate not in key_influencers:
            key_influencers.append(candidate)
        else:
            break

    return RelationshipMap(
        primary_decision_partner=primary_decision_partner,
        key_influencers=key_influencers,
        trust_network=trust_network,
    )


# ---------------------------------------------------------------------------
# immutable_constraints
# ---------------------------------------------------------------------------


def _derive_immutable_constraints(persona: PersonaRecord) -> ImmutableConstraints:
    """Assemble ImmutableConstraints.

    budget_ceiling:
      If economic_constraint_level > 0.7 → "Tight budget — {income_bracket} income"
      Else None.

    non_negotiables:
      Items from key_tensions that represent hard limits.
      Patterns "vs_budget" or "vs_constraint" trigger inclusion.
      At least 1 item if key_tensions is non-empty.

    absolute_avoidances:
      Copied from existing persona.memory.core.immutable_constraints if present,
      else empty list.
    """
    # Budget ceiling.
    values_cat: dict[str, Any] = persona.attributes.get("values", {})
    ec_attr = values_cat.get("economic_constraint_level")
    income_bracket = persona.demographic_anchor.household.income_bracket

    budget_ceiling: str | None = None
    if ec_attr is not None and isinstance(ec_attr.value, (int, float)):
        if float(ec_attr.value) > 0.7:
            budget_ceiling = f"Tight budget — {income_bracket} income"
    # Fallback: if attribute is missing but we have an income bracket, leave as None
    # (we can't determine constraint level without the attribute).

    # Non-negotiables from key_tensions.
    key_tensions: list[str] = persona.derived_insights.key_tensions
    non_negotiables: list[str] = []

    # Patterns indicating a hard constraint.
    hard_limit_patterns = [
        "vs_budget", "vs_constraint", "budget", "constraint",
        "constrain", "limit", "ceiling", "hard",
    ]

    for tension in key_tensions:
        tension_lower = tension.lower()
        if any(pat in tension_lower for pat in hard_limit_patterns):
            non_negotiables.append(tension)

    # If no pattern matches but tensions exist, include at least the first one.
    if not non_negotiables and key_tensions:
        non_negotiables.append(key_tensions[0])

    # Absolute avoidances: preserve from existing core memory if present,
    # else empty list (populated from narrative context in deeper modes).
    absolute_avoidances: list[str] = []
    try:
        existing = persona.memory.core.immutable_constraints.absolute_avoidances
        if existing:
            absolute_avoidances = list(existing)
    except AttributeError:
        pass

    return ImmutableConstraints(
        budget_ceiling=budget_ceiling,
        non_negotiables=non_negotiables,
        absolute_avoidances=absolute_avoidances,
    )


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = ["assemble_core_memory"]
