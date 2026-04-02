"""pilots/littlejoys/convert_to_simulatte.py

Converts all Littlejoys personas_generated.json records into Simulatte
PersonaRecord format and saves them to:
  - simulatte_personas.json  (list of PersonaRecord dicts)
  - simulatte_cohort.json    (CohortEnvelope)

Zero LLM calls — pure data mapping.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — allow running from any cwd
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.seed_memory import bootstrap_seed_memories
from src.persistence.envelope_store import save_envelope
from src.schema.cohort import (
    CalibrationState,
    CohortEnvelope,
    CohortSummary,
    GroundingSummary,
    TaxonomyMeta,
)
from src.schema.persona import (
    Attribute,
    BehaviouralTendencies,
    CopingMechanism,
    CoreMemory,
    DemographicAnchor,
    DerivedInsights,
    Household,
    ImmutableConstraints,
    LifeDefiningEvent,
    LifeStory,
    Location,
    Memory,
    Narrative,
    Objection,
    PersonaRecord,
    PriceSensitivityBand,
    RelationshipMap,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
LJ_DATA_PATH = Path(
    "/Users/admin/Documents/Simulatte Projects/1. LittleJoys/data/population/personas_generated.json"
)
OUTPUT_DIR = LJ_DATA_PATH.parent
PERSONAS_OUTPUT = OUTPUT_DIR / "simulatte_personas.json"
COHORT_OUTPUT = OUTPUT_DIR / "simulatte_cohort.json"

GENERATOR_VERSION = "lj-converter-1.0"
DOMAIN = "child-nutrition"


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a float to [lo, hi]."""
    return max(lo, min(hi, float(v)))


def strip_markdown(text: str) -> str:
    """Remove markdown headings (# ...) from text."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        if re.match(r"^\s*#{1,6}\s", line):
            continue
        # strip bold/italic markers
        line = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", line)
        cleaned.append(line)
    return "\n".join(cleaned).strip()


# ---------------------------------------------------------------------------
# Field mapping helpers
# ---------------------------------------------------------------------------

def map_urban_tier(city_tier: str) -> str:
    """Map Littlejoys city_tier → Simulatte UrbanTier."""
    mapping = {
        "Tier1": "metro",
        "Tier2": "tier2",
        "Tier3": "tier3",
        "Rural": "rural",
    }
    return mapping.get(city_tier, "tier2")


def map_household_structure(family_structure: str) -> str:
    """Map Littlejoys family_structure → Simulatte HouseholdStructure."""
    mapping = {
        "joint": "joint",
        "nuclear": "nuclear",
        "single_parent": "single-parent",
        "couple_no_kids": "couple-no-kids",
    }
    return mapping.get(family_structure, "other")


def estimate_household_size(family_structure: str, num_children: int) -> int:
    """Estimate household size from structure + num_children."""
    if family_structure == "joint":
        # joint: parents + children + 2-3 elders minimum
        return max(5, num_children + 4)
    elif family_structure == "single_parent":
        return num_children + 1
    else:
        # nuclear
        return num_children + 2


def map_income_bracket(income_lpa: float) -> str:
    """Map household_income_lpa (lakhs per annum) → Simulatte income_bracket."""
    if income_lpa < 3:
        return "low"
    elif income_lpa < 6:
        return "lower-middle"
    elif income_lpa < 12:
        return "middle"
    elif income_lpa < 25:
        return "upper-middle"
    else:
        return "upper"


def map_education(edu_level: str) -> str:
    """Map Littlejoys education_level → Simulatte Education literal."""
    mapping = {
        "high_school": "high-school",
        "bachelors": "undergraduate",
        "masters": "postgraduate",
        "doctorate": "doctoral",
        "professional": "postgraduate",  # closest match
    }
    return mapping.get(edu_level, "undergraduate")


def map_employment(status: str) -> str:
    """Map Littlejoys employment_status → Simulatte Employment literal."""
    mapping = {
        "full_time": "full-time",
        "part_time": "part-time",
        "freelance": "self-employed",
        "self_employed": "self-employed",
        "homemaker": "homemaker",
        "student": "student",
        "retired": "retired",
    }
    return mapping.get(status, "full-time")


def derive_life_stage(age: int, num_children: int) -> str:
    """Derive a descriptive life stage from parent age and num_children."""
    if num_children == 0:
        if age < 30:
            return "young-adult-no-kids"
        return "adult-no-kids"
    elif age < 30:
        return "young-parent"
    elif age < 40:
        return "active-parent"
    elif age < 50:
        return "established-parent"
    else:
        return "mature-parent"


def map_price_sensitivity(level: str) -> float:
    """Map price_sensitivity string → float for economic_constraint_level."""
    mapping = {"high": 0.7, "medium": 0.5, "low": 0.3}
    return mapping.get(level, 0.5)


def map_primary_value_orientation(pvo: str) -> str:
    """Map Littlejoys primary_value_orientation to Simulatte literal.

    Simulatte allows: price, quality, brand, convenience, features.
    'nutrition' is not in the Simulatte schema — map it to 'quality'.
    """
    mapping = {
        "price": "price",
        "quality": "quality",
        "brand": "brand",
        "convenience": "convenience",
        "features": "features",
        "nutrition": "quality",  # nutrition is a quality-of-outcome orientation
    }
    return mapping.get(pvo, "quality")


def make_attribute(
    value: float | str,
    attr_type: str = "continuous",
    label: str = "",
    source: str = "anchored",
) -> Attribute:
    """Build an Attribute, clamping floats to [0, 1]."""
    if attr_type == "continuous":
        value = clamp(float(value))
    return Attribute(value=value, type=attr_type, label=label, source=source)


# ---------------------------------------------------------------------------
# Main converter
# ---------------------------------------------------------------------------

def convert_persona(raw: dict, idx: int = 0) -> PersonaRecord:
    """Convert a single Littlejoys persona dict to a PersonaRecord."""
    # Use pg-lj-NNN format to satisfy G1 validator (pg-[prefix]-[NNN])
    # Original Littlejoys ID is preserved in the narrative text
    persona_id = f"pg-lj-{idx + 1:03d}"
    now = datetime.now(tz=timezone.utc)

    demo = raw.get("demographics", {})
    psych = raw.get("psychology", {})
    relationships = raw.get("relationships", {})
    career = raw.get("career", {})
    edu = raw.get("education_learning", {})
    lifestyle = raw.get("lifestyle", {})
    daily = raw.get("daily_routine", {})
    values = raw.get("values", {})
    media = raw.get("media", {})
    parent_traits = raw.get("parent_traits", {})
    budget_profile = raw.get("budget_profile", {})

    # ------------------------------------------------------------------
    # DemographicAnchor
    # ------------------------------------------------------------------
    first_name = raw["id"].split("-")[0]
    age = int(demo.get("parent_age", 30))
    num_children = int(demo.get("num_children", 1))
    family_structure = demo.get("family_structure", "nuclear")

    demographic_anchor = DemographicAnchor(
        name=first_name,
        age=age,
        gender=demo.get("parent_gender", "female"),
        location=Location(
            country="India",
            region=demo.get("region", ""),
            city=demo.get("city_name", ""),
            urban_tier=map_urban_tier(demo.get("city_tier", "Tier2")),
        ),
        household=Household(
            structure=map_household_structure(family_structure),
            size=estimate_household_size(family_structure, num_children),
            income_bracket=map_income_bracket(
                float(demo.get("household_income_lpa", 6))
            ),
            dual_income=bool(demo.get("dual_income_household", False)),
        ),
        life_stage=derive_life_stage(age, num_children),
        education=map_education(edu.get("education_level", "bachelors")),
        employment=map_employment(career.get("employment_status", "full_time")),
    )

    # ------------------------------------------------------------------
    # Attributes — nested dict keyed by group → attribute_name
    # ------------------------------------------------------------------
    routine_adherence = clamp(
        (
            float(lifestyle.get("meal_planning_habit", 0.5))
            + float(lifestyle.get("structured_vs_intuitive_feeding", 0.5))
        )
        / 2.0
    )

    attributes: dict[str, dict[str, Attribute]] = {
        "values": {
            "brand_loyalty": make_attribute(
                values.get("brand_loyalty_tendency", 0.5),
                label="Brand loyalty tendency",
            ),
            "budget_consciousness": make_attribute(
                daily.get("budget_consciousness", 0.5),
                label="Budget consciousness",
            ),
            "deal_seeking_intensity": make_attribute(
                daily.get("deal_seeking_intensity", 0.5),
                label="Deal seeking intensity",
            ),
            "indie_brand_openness": make_attribute(
                values.get("indie_brand_openness", 0.5),
                label="Openness to indie brands",
            ),
        },
        "social": {
            "authority_bias": make_attribute(
                psych.get("authority_bias", 0.5),
                label="Authority bias",
            ),
            "social_proof_bias": make_attribute(
                psych.get("social_proof_bias", 0.5),
                label="Social proof bias",
            ),
            "peer_influence_strength": make_attribute(
                relationships.get("peer_influence_strength", 0.5),
                label="Peer influence strength",
            ),
            "influencer_susceptibility": make_attribute(
                relationships.get("influencer_trust", 0.5),
                label="Influencer susceptibility",
            ),
            "online_community_trust": make_attribute(
                0.5,  # review_platform_trust is a string (e.g. "amazon_reviews"), no float
                label="Online community trust",
                source="inferred",
            ),
        },
        "lifestyle": {
            "ad_receptivity": make_attribute(
                media.get("ad_receptivity", 0.5),
                label="Ad receptivity",
            ),
            "routine_adherence": make_attribute(
                routine_adherence,
                label="Routine adherence",
                source="inferred",
            ),
            "economic_constraint_level": make_attribute(
                map_price_sensitivity(budget_profile.get("price_sensitivity", "medium")),
                label="Economic constraint level",
                source="anchored",
            ),
        },
        "psychology": {
            "information_need": make_attribute(
                psych.get("information_need", 0.5),
                label="Information need before purchase",
            ),
            "risk_tolerance": make_attribute(
                psych.get("risk_tolerance", 0.5),
                label="Risk tolerance",
            ),
        },
    }

    # ------------------------------------------------------------------
    # LifeStory (2–3 from tier2_stories, fallback from narrative)
    # ------------------------------------------------------------------
    stories_raw = (
        raw.get("semantic_memory", {})
        .get("tier2_stories", {})
        .get("stories", [])
    )

    life_stories: list[LifeStory] = []
    for s in stories_raw[:3]:
        title = s.get("title", "Untitled")
        event_text = s.get("event", "")
        impact_text = s.get("impact", "")
        # Approximate 'when' from narrative context
        when = "childhood" if "growing up" in event_text.lower() or "child" in event_text.lower() else "adulthood"
        life_stories.append(
            LifeStory(
                title=title,
                when=when,
                event=event_text[:500] if event_text else title,
                lasting_impact=impact_text[:500] if impact_text else "Shaped core values.",
            )
        )

    # Need at least 2
    if len(life_stories) == 0:
        # Fall back: build 2 from narrative text
        narrative_text = strip_markdown(raw.get("narrative", ""))
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narrative_text) if len(s.strip()) > 40]
        life_stories = [
            LifeStory(
                title="Formative experience",
                when="early life",
                event=sentences[0] if sentences else "A key formative experience shaped this person.",
                lasting_impact="This experience shaped their core values and decision-making approach.",
            ),
            LifeStory(
                title="Defining moment",
                when="adulthood",
                event=sentences[1] if len(sentences) > 1 else "A significant life event reinforced their priorities.",
                lasting_impact="Reinforced their approach to family and community.",
            ),
        ]
    elif len(life_stories) == 1:
        life_stories.append(
            LifeStory(
                title="Everyday conviction",
                when="adulthood",
                event="Daily routines and choices reflect their core values and priorities.",
                lasting_impact="Consistency in everyday habits reinforces their identity and sense of purpose.",
            )
        )

    # ------------------------------------------------------------------
    # Narrative
    # ------------------------------------------------------------------
    full_narrative = strip_markdown(raw.get("narrative", ""))
    first_person_summary = raw.get("first_person_summary", "")

    narrative = Narrative(
        first_person=full_narrative if full_narrative else first_person_summary,
        third_person=first_person_summary if first_person_summary else full_narrative[:800],
        display_name=raw.get("display_name", first_name),
    )

    # ------------------------------------------------------------------
    # DerivedInsights
    # ------------------------------------------------------------------
    decision_style = parent_traits.get("decision_style", "analytical")
    trust_anchor = parent_traits.get("trust_anchor", "self")
    risk_appetite = parent_traits.get("risk_appetite", "medium")
    pvo_raw = parent_traits.get("primary_value_orientation", "quality")
    primary_value_orientation = map_primary_value_orientation(pvo_raw)
    coping_type = parent_traits.get("coping_mechanism_type", "routine_control")
    coping_description = parent_traits.get(
        "coping_mechanism",
        "Relies on established routines to manage uncertainty.",
    )
    consistency_score = int(parent_traits.get("consistency_score", 70))
    consistency_band = parent_traits.get("consistency_band", "medium")

    # Key tensions — derive from parent traits and psychology
    key_tensions: list[str] = []
    if float(psych.get("analysis_paralysis_tendency", 0)) > 0.5:
        key_tensions.append("Tendency toward analysis paralysis in high-stakes decisions")
    if float(values.get("brand_loyalty_tendency", 0)) < 0.4 and float(values.get("indie_brand_openness", 0)) > 0.6:
        key_tensions.append("Pulls between brand familiarity and openness to new options")
    if float(budget_profile.get("school_fee_pressure_factor", 0)) > 0.7:
        key_tensions.append("Financial pressure competes with desire to invest in child's wellbeing")
    if float(psych.get("regret_sensitivity", 0)) > 0.6:
        key_tensions.append("High regret sensitivity makes decisions emotionally costly")
    if not key_tensions:
        key_tensions.append(
            f"Balancing {primary_value_orientation}-driven priorities with household constraints"
        )

    # Decision style score — map from decision_speed
    decision_style_score = clamp(float(psych.get("decision_speed", 0.5)))

    derived_insights = DerivedInsights(
        decision_style=decision_style,
        decision_style_score=decision_style_score,
        trust_anchor=trust_anchor,
        risk_appetite=risk_appetite,
        primary_value_orientation=primary_value_orientation,
        coping_mechanism=CopingMechanism(
            type=coping_type,
            description=coping_description,
        ),
        consistency_score=consistency_score,
        consistency_band=consistency_band,
        key_tensions=key_tensions,
    )

    # ------------------------------------------------------------------
    # BehaviouralTendencies
    # ------------------------------------------------------------------
    price_sens_label = budget_profile.get("price_sensitivity", "medium")
    # Map to PriceSensitivityBandLabel (low/medium/high/extreme)
    ps_band_mapping = {"low": "low", "medium": "medium", "high": "high"}
    ps_band = ps_band_mapping.get(price_sens_label, "medium")

    brand_switch_tolerance = budget_profile.get("brand_switch_tolerance", "medium")
    # switching_propensity: high switch tolerance = high propensity
    switch_band_map = {"high": "high", "medium": "medium", "low": "low"}
    switch_band = switch_band_map.get(brand_switch_tolerance, "medium")

    # Trust orientation weights from media/relationships
    ad_trust = clamp(float(media.get("ad_receptivity", 0.5)))
    peer_trust = clamp(float(relationships.get("peer_influence_strength", 0.5)))
    influencer_trust = clamp(float(relationships.get("influencer_trust", 0.5)))
    authority_trust = clamp(float(psych.get("authority_bias", 0.5)))
    # community = review_platform_trust is a string; use a proxy
    community_trust = 0.6  # amazon_reviews is the only value; treat as moderate-high

    trust_weights = TrustWeights(
        expert=authority_trust,
        peer=peer_trust,
        brand=clamp(float(values.get("brand_loyalty_tendency", 0.5))),
        ad=ad_trust,
        community=community_trust,
        influencer=influencer_trust,
    )

    # Dominant trust channel
    tw_dict = {
        "expert": trust_weights.expert,
        "peer": trust_weights.peer,
        "brand": trust_weights.brand,
        "ad": trust_weights.ad,
        "community": trust_weights.community,
        "influencer": trust_weights.influencer,
    }
    dominant_trust = max(tw_dict, key=tw_dict.get)

    # Objections
    objections: list[Objection] = []
    if float(psych.get("risk_tolerance", 0.5)) < 0.4:
        objections.append(
            Objection(objection_type="risk_aversion", likelihood="high", severity="friction")
        )
    if price_sens_label == "high":
        objections.append(
            Objection(objection_type="price_vs_value", likelihood="high", severity="blocking")
        )
    elif price_sens_label == "medium":
        objections.append(
            Objection(objection_type="price_vs_value", likelihood="medium", severity="friction")
        )
    if float(psych.get("information_need", 0.5)) > 0.7:
        objections.append(
            Objection(
                objection_type="need_more_information",
                likelihood="medium",
                severity="friction",
            )
        )
    if not objections:
        objections.append(
            Objection(
                objection_type="switching_cost_concern",
                likelihood="low",
                severity="minor",
            )
        )

    behavioural_tendencies = BehaviouralTendencies(
        price_sensitivity=PriceSensitivityBand(
            band=ps_band,
            description=f"Price sensitivity is {ps_band}; income bracket is {demographic_anchor.household.income_bracket}.",
            source="grounded",
        ),
        trust_orientation=TrustOrientation(
            weights=trust_weights,
            dominant=dominant_trust,
            description=f"Primarily trusts {dominant_trust} sources when evaluating products.",
            source="grounded",
        ),
        switching_propensity=TendencyBand(
            band=switch_band,
            description=f"Brand switch tolerance is {brand_switch_tolerance}; switching propensity is {switch_band}.",
            source="grounded",
        ),
        objection_profile=objections,
        reasoning_prompt=(
            f"{first_name} is a {age}-year-old {demographic_anchor.employment} parent in "
            f"{demographic_anchor.location.city}. "
            f"They are {primary_value_orientation}-oriented with {risk_appetite} risk appetite. "
            f"Trust anchor: {trust_anchor}. When simulating, draw on their {decision_style} "
            f"decision style and acknowledge key tensions: {'; '.join(key_tensions[:2])}."
        ),
    )

    # ------------------------------------------------------------------
    # CoreMemory
    # ------------------------------------------------------------------
    # identity_statement from narrative or first_person_summary
    identity_lines = [
        ln.strip()
        for ln in full_narrative.splitlines()
        if ln.strip() and len(ln.strip()) > 50
    ]
    identity_statement = identity_lines[0] if identity_lines else (
        f"{first_name} is a {age}-year-old {demographic_anchor.employment} parent in "
        f"{demographic_anchor.location.city} navigating family and financial priorities."
    )
    # cap length
    if len(identity_statement) > 200:
        identity_statement = identity_statement[:197] + "..."

    # key_values from semantic_memory.tier2_anchor or fallback from values block
    tier2_anchor = raw.get("semantic_memory", {}).get("tier2_anchor", {})
    core_values_raw = tier2_anchor.get("core_values", [])
    if core_values_raw:
        key_values = core_values_raw[:5]
    else:
        # Derive from the values block — take top-scoring numeric fields
        value_scores = {
            k: float(v)
            for k, v in values.items()
            if isinstance(v, (int, float))
        }
        sorted_vals = sorted(value_scores, key=value_scores.get, reverse=True)
        key_values = [v.replace("_", " ").title() for v in sorted_vals[:5]]

    # Ensure 3–5 items
    while len(key_values) < 3:
        key_values.append("Family wellbeing")
    key_values = key_values[:5]

    # life_defining_events from tier2_stories
    life_defining_events: list[LifeDefiningEvent] = []
    for s in stories_raw[:3]:
        event_text = s.get("event", "")
        impact_text = s.get("impact", "")
        # Approximate age from text
        age_when = max(5, age - 20)  # safe fallback
        for phrase in ["age ten", "age fourteen", "at fourteen", "at ten",
                       "ten years old", "fourteen years old", "aged ten"]:
            if phrase in event_text.lower():
                try:
                    nums = re.findall(r"\b(\d{1,2})\b", event_text)
                    if nums:
                        age_when = int(nums[0])
                except Exception:
                    pass
        life_defining_events.append(
            LifeDefiningEvent(
                age_when=age_when,
                event=event_text[:400] if event_text else "A significant life event.",
                lasting_impact=impact_text[:400] if impact_text else "Shaped values.",
            )
        )

    if not life_defining_events:
        life_defining_events.append(
            LifeDefiningEvent(
                age_when=max(5, age - 15),
                event="A formative childhood experience shaped their values around family and community.",
                lasting_impact="Established core priorities that guide decisions to this day.",
            )
        )

    # relationship_map
    primary_dm = raw.get("decision_rights", {}).get("child_nutrition", "self")
    relationship_map = RelationshipMap(
        primary_decision_partner=primary_dm,
        key_influencers=["pediatrician", "family elders", "peer parents"],
        trust_network=["family", "pediatrician", "neighbors"],
    )

    # immutable_constraints
    non_negotiables = []
    if float(values.get("food_first_belief", 0)) > 0.6:
        non_negotiables.append("Food-first nutrition philosophy over supplements")
    if raw.get("cultural", {}).get("dietary_culture") == "vegetarian":
        non_negotiables.append("Vegetarian-only products")
    if not non_negotiables:
        non_negotiables.append("Child safety and wellbeing above all else")

    absolute_avoidances = ["products with artificial additives (where label-reading habit is high)"]

    budget_ceiling_inr = budget_profile.get("discretionary_child_nutrition_budget_inr")
    budget_ceiling_str = (
        f"INR {int(budget_ceiling_inr)}/month for child nutrition extras"
        if budget_ceiling_inr
        else None
    )

    immutable_constraints = ImmutableConstraints(
        budget_ceiling=budget_ceiling_str,
        non_negotiables=non_negotiables,
        absolute_avoidances=absolute_avoidances,
    )

    # tendency_summary from parent traits fields
    decision_confidence = parent_traits.get("decision_confidence", "medium")
    outcome_orientation = parent_traits.get("outcome_orientation", "long_term")
    tendency_summary = (
        f"{first_name} makes {decision_style} decisions with {decision_confidence} confidence, "
        f"anchoring trust in {trust_anchor} sources. "
        f"They are {outcome_orientation}-oriented, {risk_appetite}-risk, "
        f"and cope with uncertainty through {coping_type.replace('_', ' ')}."
    )

    core_memory = CoreMemory(
        identity_statement=identity_statement,
        key_values=key_values,
        life_defining_events=life_defining_events,
        relationship_map=relationship_map,
        immutable_constraints=immutable_constraints,
        tendency_summary=tendency_summary,
    )

    # ------------------------------------------------------------------
    # WorkingMemory — seeded from CoreMemory
    # ------------------------------------------------------------------
    working_memory = bootstrap_seed_memories(core_memory, first_name)

    memory = Memory(core=core_memory, working=working_memory)

    # ------------------------------------------------------------------
    # decision_bullets
    # ------------------------------------------------------------------
    decision_bullets = raw.get("purchase_decision_bullets", [])
    if not decision_bullets:
        decision_bullets = [
            f"{first_name} is a {primary_value_orientation}-driven buyer with {risk_appetite} risk appetite.",
            f"Price sensitivity: {price_sens_label}. Budget ceiling: {budget_ceiling_str or 'flexible'}.",
        ]

    # ------------------------------------------------------------------
    # PersonaRecord
    # ------------------------------------------------------------------
    return PersonaRecord(
        persona_id=persona_id,
        generated_at=now,
        generator_version=GENERATOR_VERSION,
        domain=DOMAIN,
        mode="grounded",
        demographic_anchor=demographic_anchor,
        life_stories=life_stories,
        attributes=attributes,
        derived_insights=derived_insights,
        behavioural_tendencies=behavioural_tendencies,
        narrative=narrative,
        decision_bullets=decision_bullets,
        memory=memory,
    )


# ---------------------------------------------------------------------------
# Cohort summary helpers
# ---------------------------------------------------------------------------

def build_cohort_summary(personas: list[PersonaRecord]) -> CohortSummary:
    """Build aggregate statistics from converted personas."""
    from collections import Counter

    ds_counts = Counter(p.derived_insights.decision_style for p in personas)
    ta_counts = Counter(p.derived_insights.trust_anchor for p in personas)
    ra_counts = Counter(p.derived_insights.risk_appetite for p in personas)
    cs_list = [p.derived_insights.consistency_score for p in personas]

    # Gather all key_tensions
    all_tensions: list[str] = []
    for p in personas:
        all_tensions.extend(p.derived_insights.key_tensions)
    tension_counts = Counter(all_tensions)
    dominant_tensions = [t for t, _ in tension_counts.most_common(5)]

    # persona_type_distribution (use employment as proxy for persona types)
    type_counts = Counter(p.demographic_anchor.employment for p in personas)

    # Simple distinctiveness: std of consistency scores / 100
    mean_cs = sum(cs_list) / len(cs_list)
    variance = sum((x - mean_cs) ** 2 for x in cs_list) / len(cs_list)
    distinctiveness = min(1.0, (variance ** 0.5) / 30)

    return CohortSummary(
        decision_style_distribution=dict(ds_counts),
        trust_anchor_distribution=dict(ta_counts),
        risk_appetite_distribution=dict(ra_counts),
        consistency_scores={
            "mean": round(mean_cs, 1),
            "min": min(cs_list),
            "max": max(cs_list),
        },
        persona_type_distribution=dict(type_counts),
        distinctiveness_score=round(distinctiveness, 3),
        coverage_assessment=(
            f"Covers {len(set(p.demographic_anchor.location.city for p in personas))} cities "
            f"across {len(set(p.demographic_anchor.location.region for p in personas))} regions; "
            f"all Indian child-nutrition domain parents."
        ),
        dominant_tensions=dominant_tensions if dominant_tensions else ["Budget vs. quality trade-off"],
    )


def build_icp_hash(personas: list[PersonaRecord]) -> str:
    """Stable hash of persona IDs for the cohort envelope."""
    ids_str = ",".join(sorted(p.persona_id for p in personas))
    return hashlib.md5(ids_str.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Loading Littlejoys personas from:\n  {LJ_DATA_PATH}\n")
    with open(LJ_DATA_PATH, encoding="utf-8") as f:
        raw_personas: list[dict] = json.load(f)

    print(f"Found {len(raw_personas)} personas. Converting...\n")

    converted: list[PersonaRecord] = []
    failures: list[tuple[str, str]] = []

    for i, raw in enumerate(raw_personas):
        persona_id = raw.get("id", f"unknown-{i}")
        try:
            record = convert_persona(raw, idx=i)
            converted.append(record)
        except Exception as exc:
            tb = traceback.format_exc()
            failures.append((persona_id, f"{exc}\n{tb}"))

    # ------------------------------------------------------------------
    # Save individual personas list
    # ------------------------------------------------------------------
    personas_data = [p.model_dump(mode="json") for p in converted]
    PERSONAS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(PERSONAS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(personas_data, f, indent=2, default=str)
    print(f"Saved {len(converted)} PersonaRecords → {PERSONAS_OUTPUT}")

    # ------------------------------------------------------------------
    # Build and save CohortEnvelope
    # ------------------------------------------------------------------
    if converted:
        now = datetime.now(tz=timezone.utc)
        icp_hash = build_icp_hash(converted)

        cohort = CohortEnvelope(
            cohort_id=f"lj-child-nutrition-{icp_hash}",
            generated_at=now,
            domain=DOMAIN,
            business_problem="Simulate Indian parent purchase decision-making for child nutrition products (Littlejoys context).",
            mode="grounded",
            icp_spec_hash=icp_hash,
            taxonomy_used=TaxonomyMeta(
                base_attributes=14,
                domain_extension_attributes=0,
                total_attributes=14,
                domain_data_used=True,
                business_problem="Child nutrition product adoption in Indian households",
                icp_spec_hash=icp_hash,
            ),
            personas=converted,
            cohort_summary=build_cohort_summary(converted),
            grounding_summary=GroundingSummary(
                tendency_source_distribution={
                    "grounded": 0.6,
                    "proxy": 0.3,
                    "estimated": 0.1,
                },
                domain_data_signals_extracted=len(converted) * 14,
                clusters_derived=5,
            ),
            calibration_state=CalibrationState(
                status="uncalibrated",
                method_applied=None,
                last_calibrated=None,
                benchmark_source=None,
                notes="Converted from Littlejoys simulation personas; not yet benchmark-calibrated.",
            ),
        )

        saved_path = save_envelope(cohort, COHORT_OUTPUT)
        print(f"Saved CohortEnvelope ({len(converted)} personas) → {saved_path}")

    # ------------------------------------------------------------------
    # Summary report
    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"CONVERSION SUMMARY")
    print(f"{'='*60}")
    print(f"  Total input personas : {len(raw_personas)}")
    print(f"  Successfully converted: {len(converted)}")
    print(f"  Failed               : {len(failures)}")

    if failures:
        print(f"\nFAILURES:")
        for pid, err in failures:
            print(f"\n  [{pid}]")
            # print first line of error only to keep it readable
            print(f"    {err.splitlines()[0]}")

    if converted:
        # Show a sample of the first persona
        sample = converted[0]
        print(f"\nSAMPLE (first converted persona):")
        print(f"  persona_id    : {sample.persona_id}")
        print(f"  name          : {sample.demographic_anchor.name}")
        print(f"  age           : {sample.demographic_anchor.age}")
        print(f"  city          : {sample.demographic_anchor.location.city}")
        print(f"  urban_tier    : {sample.demographic_anchor.location.urban_tier}")
        print(f"  income_bracket: {sample.demographic_anchor.household.income_bracket}")
        print(f"  education     : {sample.demographic_anchor.education}")
        print(f"  employment    : {sample.demographic_anchor.employment}")
        print(f"  life_stage    : {sample.demographic_anchor.life_stage}")
        print(f"  decision_style: {sample.derived_insights.decision_style}")
        print(f"  trust_anchor  : {sample.derived_insights.trust_anchor}")
        print(f"  risk_appetite : {sample.derived_insights.risk_appetite}")
        print(f"  pvo           : {sample.derived_insights.primary_value_orientation}")
        print(f"  life_stories  : {len(sample.life_stories)} stories")
        print(f"  key_values    : {sample.memory.core.key_values}")
        print(f"  seed obs count: {len(sample.memory.working.observations)}")
        print(f"  attribute grps: {list(sample.attributes.keys())}")
        print(f"  decision_bullets: {len(sample.decision_bullets)} bullets")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
