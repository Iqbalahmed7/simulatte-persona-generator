"""tests/fixtures/synthetic_persona.py — Factory for synthetic PersonaRecord objects.

Used by BV1 and BV2 integration tests. No LLM calls.
Uses fixed values for test reproducibility.

Persona: Priya Mehta, 34, Mumbai, budget-conscious, family-focused, peer trust dominant.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.schema.persona import (
    Attribute,
    BehaviouralTendencies,
    CoreMemory,
    DemographicAnchor,
    DerivedInsights,
    CopingMechanism,
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
    SimulationState,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
    WorkingMemory,
)
from src.schema.validators import PersonaValidator
from src.memory.seed_memory import bootstrap_seed_memories


def make_synthetic_persona() -> PersonaRecord:
    """
    Returns a minimal but fully valid PersonaRecord for use in BV tests.

    Uses fixed values — not randomised — for test reproducibility.

    Character: Priya Mehta, 34, Mumbai.
    Profile: budget-conscious professional, family-focused, peer trust dominant.
    Decision style: social (peer-validated), moderate risk aversion, high price sensitivity.

    Attribute choices satisfy all G1-G3 validators:
    - TR1: budget_consciousness=0.80 (>0.70) → price_sensitivity.band="high"
    - TR4: social_proof_bias=0.75 (>0.65) → trust_weights.peer=0.75 (>=0.65)
    - TR6: ad_receptivity=0.22 (<0.30) → trust_weights.ad=0.15 (<=0.25)
    - TR8: risk_tolerance=0.25 (<0.30) → objection includes "risk_aversion"
    - HC1: income_bracket="middle" (no poverty keyword) — no violation
    - HC2: urban_tier="metro" — no violation
    - HC4: age=34 (>=25) — no violation
    - HC5: income_bracket="middle" (no high/top keyword) — no violation
    - HC6: risk_tolerance=0.25, loss_aversion=0.60 — not both >0.80
    """
    now = datetime.now(timezone.utc)

    # --- Demographic Anchor ---
    demographic_anchor = DemographicAnchor(
        name="Priya Mehta",
        age=34,
        gender="female",
        location=Location(
            country="India",
            region="Maharashtra",
            city="Mumbai",
            urban_tier="metro",
        ),
        household=Household(
            structure="nuclear",
            size=4,
            income_bracket="middle",
            dual_income=True,
        ),
        life_stage="early-family",
        education="undergraduate",
        employment="full-time",
    )

    # --- Life Stories (2-3 required) ---
    life_stories = [
        LifeStory(
            title="First independent purchase",
            when="age 22",
            event="Bought my first smartphone with my own savings after months of comparison.",
            lasting_impact="Reinforced that careful research and peer advice saves money and prevents regret.",
        ),
        LifeStory(
            title="Having my first child",
            when="age 30",
            event="Became a mother and had to rethink every household expense with a newborn.",
            lasting_impact="Family safety and value-for-money now override personal indulgences entirely.",
        ),
        LifeStory(
            title="Neighbour's bad experience with a premium brand",
            when="age 32",
            event="A close neighbour spent heavily on a premium brand that failed within months.",
            lasting_impact="Confirmed that price alone does not signal quality; peer experience matters more.",
        ),
    ]

    # --- Attributes ---
    # Carefully constructed to pass all TR rules:
    # TR1: budget_consciousness=0.80 >0.70 → price_sensitivity "high" ✓
    # TR4: social_proof_bias=0.75 >0.65 → trust_weights.peer=0.75 >=0.65 ✓
    # TR6: ad_receptivity=0.22 <0.30 → trust_weights.ad=0.15 <=0.25 ✓
    # TR8: risk_tolerance=0.25 <0.30 → objection_profile includes "risk_aversion" ✓
    # AttributeSource literals: "sampled" | "inferred" | "anchored" | "domain_data"
    attributes: dict[str, dict[str, Attribute]] = {
        "values": {
            "budget_consciousness": Attribute(
                value=0.80,
                type="continuous",
                label="High budget consciousness",
                source="anchored",
            ),
            "brand_loyalty": Attribute(
                value=0.55,
                type="continuous",
                label="Moderate brand loyalty",
                source="anchored",
            ),
            "premium_quality_preference": Attribute(
                value=0.50,
                type="continuous",
                label="Moderate quality preference",
                source="anchored",
            ),
            "deal_seeking_intensity": Attribute(
                value=0.72,
                type="continuous",
                label="High deal-seeking",
                source="anchored",
            ),
            "primary_value_driver": Attribute(
                value="price",
                type="categorical",
                label="Price-driven value orientation",
                source="anchored",
            ),
        },
        "psychology": {
            "risk_tolerance": Attribute(
                value=0.25,
                type="continuous",
                label="Low risk tolerance",
                source="anchored",
            ),
            "loss_aversion": Attribute(
                value=0.60,
                type="continuous",
                label="Moderate-high loss aversion",
                source="anchored",
            ),
            "health_anxiety": Attribute(
                value=0.45,
                type="continuous",
                label="Moderate health anxiety",
                source="anchored",
            ),
            "information_need": Attribute(
                value=0.65,
                type="continuous",
                label="Moderate-high information need",
                source="anchored",
            ),
            "personality_type": Attribute(
                value="analytical",
                type="categorical",
                label="Analytical personality",
                source="anchored",
            ),
        },
        "social": {
            "social_proof_bias": Attribute(
                value=0.75,
                type="continuous",
                label="High social proof sensitivity",
                source="anchored",
            ),
            "authority_bias": Attribute(
                value=0.45,
                type="continuous",
                label="Moderate authority bias",
                source="anchored",
            ),
            "social_orientation": Attribute(
                value="community",
                type="categorical",
                label="Community-oriented",
                source="anchored",
            ),
        },
        "lifestyle": {
            "ad_receptivity": Attribute(
                value=0.22,
                type="continuous",
                label="Low ad receptivity",
                source="anchored",
            ),
            "digital_payment_comfort": Attribute(
                value=0.70,
                type="continuous",
                label="High digital payment comfort",
                source="anchored",
            ),
        },
        "identity": {
            "life_stage_priority": Attribute(
                value="family-wellbeing",
                type="categorical",
                label="Family wellbeing priority",
                source="anchored",
            ),
            "tension_seed": Attribute(
                value="quality-vs-price",
                type="categorical",
                label="Quality vs price tension",
                source="anchored",
            ),
        },
    }

    # --- Derived Insights ---
    derived_insights = DerivedInsights(
        decision_style="social",
        decision_style_score=0.72,
        trust_anchor="peer",
        risk_appetite="low",
        primary_value_orientation="price",
        coping_mechanism=CopingMechanism(
            type="social_validation",
            description=(
                "Priya validates purchasing decisions by consulting trusted peers "
                "before committing, especially for non-routine or higher-cost items."
            ),
        ),
        consistency_score=78,
        consistency_band="high",
        key_tensions=[
            "Wants quality products but is constrained by a strict household budget.",
            "Trusts peer opinion over expert reviews but sometimes peers lack domain knowledge.",
        ],
    )

    # --- Behavioural Tendencies ---
    # TR1 satisfied: budget_consciousness=0.80 → price_sensitivity.band="high"
    # TR4 satisfied: social_proof_bias=0.75 → trust_weights.peer=0.75
    # TR6 satisfied: ad_receptivity=0.22 → trust_weights.ad=0.15
    # TR8 satisfied: risk_tolerance=0.25 → objection_profile includes "risk_aversion"
    behavioural_tendencies = BehaviouralTendencies(
        price_sensitivity=PriceSensitivityBand(
            band="high",
            description=(
                "Priya actively compares prices before every purchase and avoids "
                "premium tiers unless peer-validated as truly worth it."
            ),
            source="proxy",
        ),
        trust_orientation=TrustOrientation(
            weights=TrustWeights(
                expert=0.45,
                peer=0.75,
                brand=0.35,
                ad=0.15,
                community=0.65,
                influencer=0.30,
            ),
            dominant="peer",
            description=(
                "Peer opinions and community word-of-mouth are Priya's primary "
                "trust signals. Expert reviews carry secondary weight."
            ),
            source="proxy",
        ),
        switching_propensity=TendencyBand(
            band="medium",
            description=(
                "Will switch brands when peers report a clearly better value option, "
                "but does not seek novelty for its own sake."
            ),
            source="proxy",
        ),
        objection_profile=[
            Objection(
                objection_type="price_vs_value",
                likelihood="high",
                severity="friction",
            ),
            Objection(
                objection_type="risk_aversion",
                likelihood="high",
                severity="friction",
            ),
            Objection(
                objection_type="social_proof_gap",
                likelihood="medium",
                severity="friction",
            ),
        ],
        reasoning_prompt=(
            "Priya Mehta is a 34-year-old working mother in Mumbai who evaluates "
            "every purchase through the lens of family welfare and budget discipline. "
            "She relies heavily on peer word-of-mouth before committing to any "
            "non-routine spending. Price-value alignment is her primary filter, "
            "and she will defer or abandon a purchase if she cannot confirm it "
            "through her trusted social circle. Risk aversion is elevated — she "
            "strongly prefers proven options over new or unvalidated products."
        ),
    )

    # --- Narrative ---
    first_person = (
        "I am Priya Mehta, a mother of two and a working professional in Mumbai. "
        "Every purchase I make is filtered through one question: is this the best "
        "value for my family? I do not chase brands — I chase outcomes. Before I "
        "spend on anything new, I ask people I trust: my sister, my colleagues, "
        "my neighbours. Their experience matters more to me than any advertisement. "
        "I have learned the hard way that premium prices do not always mean "
        "premium results, and I refuse to gamble with my family's savings."
    )

    third_person = (
        "Priya Mehta is a 34-year-old married professional living in a nuclear "
        "household of four in Mumbai. With a dual income supporting two young "
        "children, she approaches all non-essential spending with careful scrutiny. "
        "Her decision style is deeply social: she consults a tight peer network "
        "before making any unfamiliar purchase, placing far more weight on lived "
        "experience from people she knows than on brand advertising or influencer "
        "content. She has a strong aversion to financial risk and will almost "
        "always prefer a known, peer-validated option over a newer or untested "
        "alternative. Price-value alignment is her dominant filter, and she is "
        "quick to walk away from products that cannot demonstrate clear household "
        "benefit relative to cost. Her consistency is high: she applies these "
        "criteria reliably across categories and rarely makes impulsive decisions."
    )

    narrative = Narrative(
        first_person=first_person,
        third_person=third_person,
        display_name="Priya M.",
    )

    # --- Core Memory ---
    core_memory = CoreMemory(
        identity_statement=(
            "I am a budget-conscious Mumbai mother who makes every "
            "purchase decision through the lens of family welfare, peer trust, "
            "and disciplined value-seeking."
        ),
        key_values=[
            "Family welfare above personal indulgence",
            "Peer-validated value over brand prestige",
            "Disciplined spending as self-respect",
            "Risk avoidance in unfamiliar categories",
        ],
        life_defining_events=[
            LifeDefiningEvent(
                age_when=22,
                event="First independent purchase after months of careful comparison.",
                lasting_impact="Research and peer advice prevent regret and protect savings.",
            ),
            LifeDefiningEvent(
                age_when=30,
                event="Became a mother; family safety reshaped every spending priority.",
                lasting_impact="Family welfare now overrides personal consumption preferences.",
            ),
        ],
        relationship_map=RelationshipMap(
            primary_decision_partner="husband / partner",
            key_influencers=["peer network", "close family"],
            trust_network=["sister", "colleagues", "neighbours"],
        ),
        immutable_constraints=ImmutableConstraints(
            budget_ceiling="middle-income household, dual income",
            non_negotiables=[
                "Must manage: quality-vs-price tension on every non-routine purchase",
                "Must manage: reliance on peer validation before spending",
            ],
            absolute_avoidances=[],
        ),
        tendency_summary=(
            "Priya applies a consistent peer-first, price-second filter to purchases. "
            "She defers to trusted social signals over brand or expert authority, "
            "and her elevated risk aversion means she reliably avoids novel or "
            "unvalidated options even when they offer potential upside."
        ),
    )

    # --- Working Memory (bootstrapped from core memory) ---
    working_memory = bootstrap_seed_memories(
        core_memory=core_memory,
        persona_name="Priya Mehta",
    )

    # --- Decision Bullets ---
    decision_bullets = [
        "Social decision style (score: 0.72) — peer opinion drives final call",
        "Price orientation: will not pay premium without peer validation",
        "Risk appetite: low — strongly prefers proven, known options",
        "High price sensitivity: compares costs actively before committing",
        "Objection triggers: price-vs-value, risk aversion, social proof gaps",
    ]

    # --- Assemble PersonaRecord ---
    persona = PersonaRecord(
        persona_id="pg-priya-001",
        generated_at=now,
        generator_version="4.0.0",
        domain="cpg",
        mode="simulation-ready",
        demographic_anchor=demographic_anchor,
        life_stories=life_stories,
        attributes=attributes,
        derived_insights=derived_insights,
        behavioural_tendencies=behavioural_tendencies,
        narrative=narrative,
        decision_bullets=decision_bullets,
        memory=Memory(core=core_memory, working=working_memory),
    )

    # --- Assert G1-G3 pass ---
    validator = PersonaValidator()
    results = validator.validate_all(persona)
    failures = [f for r in results for f in r.failures]
    assert not failures, (
        f"make_synthetic_persona() produced a persona that failed validation: {failures}"
    )

    return persona
