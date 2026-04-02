"""tests/test_survey_e2e.py — End-to-end integration tests for the survey pipeline.

Sprint 6 — Goose (Survey End-to-End Test)

Spec: Validity Protocol BV4 (interview realism), BV5 (adjacent persona distinction)

All three tests are @pytest.mark.integration — they make real LLM calls.
They skip automatically without --integration flag (conftest.py handles this).
Run with: pytest tests/test_survey_e2e.py --integration
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.modalities.survey import run_survey, SurveyQuestion
from src.modalities.survey_report import generate_report
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
from tests.fixtures.synthetic_persona import make_synthetic_persona


# ---------------------------------------------------------------------------
# Survey questions (5 questions for the e2e suite)
# ---------------------------------------------------------------------------

SURVEY_QUESTIONS = [
    SurveyQuestion(id="q1", text="How do you feel about trying a new brand for your household staples?", category="brand_perception"),
    SurveyQuestion(id="q2", text="Would you pay a premium for a product that claims to be healthier?", category="purchase_intent"),
    SurveyQuestion(id="q3", text="When you last made a big purchase, what was the most important factor?", category="decision_drivers"),
    SurveyQuestion(id="q4", text="How much do your friends and family influence what you buy?", category="social_influence"),
    SurveyQuestion(id="q5", text="If a trusted brand launched a new product, how quickly would you try it?", category="brand_loyalty"),
]


# ---------------------------------------------------------------------------
# Adjacent persona factory — Ritu Sharma
#
# Same Social Validator archetype as Priya but different demographics,
# life experience and tensions. Satisfies G1-G3.
#
# Attribute rules satisfied:
#   TR1: budget_consciousness=0.65 (<=0.70) — no TR1 constraint triggered
#   TR4: social_proof_bias=0.72 (>0.65) → trust_weights.peer=0.72 (>=0.65) ✓
#   TR6: ad_receptivity=0.28 (<0.30) → trust_weights.ad=0.20 (<=0.25) ✓
#   TR8: risk_tolerance=0.32 (>=0.30) — no TR8 constraint triggered
#   HC1: income_bracket="upper-middle" — no poverty keyword ✓
#   HC2: urban_tier="metro" — no violation ✓
#   HC4: age=31 (>=25) — no violation ✓
#   HC5: income_bracket="upper-middle" — does NOT contain "high" or "top" ✓
#   HC6: risk_tolerance=0.32, loss_aversion=0.50 — not both >0.80 ✓
# ---------------------------------------------------------------------------


def _make_adjacent_persona() -> PersonaRecord:
    """Build Ritu Sharma — Social Validator, 31, Delhi, marketing professional.

    Same Social Validator archetype as Priya Mehta (social_proof_bias=0.72,
    peer trust anchor) but distinct demographics, life story and tensions.
    No children. Urban professional identity. Career-driven tensions replace
    family budget tensions.

    All G1-G3 validators pass.
    """
    now = datetime.now(timezone.utc)

    # --- Demographic Anchor ---
    demographic_anchor = DemographicAnchor(
        name="Ritu Sharma",
        age=31,
        gender="female",
        location=Location(
            country="India",
            region="Delhi",
            city="Delhi",
            urban_tier="metro",
        ),
        household=Household(
            structure="couple-no-kids",
            size=2,
            income_bracket="upper-middle",
            dual_income=True,
        ),
        life_stage="early-career",
        education="postgraduate",
        employment="full-time",
    )

    # --- Life Stories (2-3 required) ---
    life_stories = [
        LifeStory(
            title="First brand betrayal at work",
            when="age 25",
            event="Recommended a product to a client based on advertising alone; it failed publicly.",
            lasting_impact="Professional reputation matters — only endorse what peers have vetted.",
        ),
        LifeStory(
            title="Colleague's product recommendation that changed categories",
            when="age 28",
            event="A respected colleague introduced me to a brand I had ignored; it became a staple.",
            lasting_impact="Peer testimony breaks inertia faster than any marketing campaign.",
        ),
        LifeStory(
            title="Premium product disappointment",
            when="age 29",
            event="Bought a premium wellness brand without asking anyone; results were mediocre.",
            lasting_impact="Price premium without social proof is just a gamble.",
        ),
    ]

    # --- Attributes ---
    # TR1: budget_consciousness=0.65 (<=0.70) — TR1 not triggered
    # TR4: social_proof_bias=0.72 (>0.65) → trust_weights.peer=0.72 >=0.65 ✓
    # TR6: ad_receptivity=0.28 (<0.30) → trust_weights.ad=0.20 <=0.25 ✓
    # TR8: risk_tolerance=0.32 (>=0.30) — TR8 not triggered
    attributes: dict[str, dict[str, Attribute]] = {
        "values": {
            "budget_consciousness": Attribute(
                value=0.65,
                type="continuous",
                label="Moderate budget consciousness",
                source="anchored",
            ),
            "brand_loyalty": Attribute(
                value=0.48,
                type="continuous",
                label="Moderate brand loyalty",
                source="anchored",
            ),
            "premium_quality_preference": Attribute(
                value=0.62,
                type="continuous",
                label="Moderate-high quality preference",
                source="anchored",
            ),
            "deal_seeking_intensity": Attribute(
                value=0.45,
                type="continuous",
                label="Moderate deal-seeking",
                source="anchored",
            ),
            "primary_value_driver": Attribute(
                value="quality",
                type="categorical",
                label="Quality-driven value orientation",
                source="anchored",
            ),
        },
        "psychology": {
            "risk_tolerance": Attribute(
                value=0.32,
                type="continuous",
                label="Low-moderate risk tolerance",
                source="anchored",
            ),
            "loss_aversion": Attribute(
                value=0.50,
                type="continuous",
                label="Moderate loss aversion",
                source="anchored",
            ),
            "health_anxiety": Attribute(
                value=0.55,
                type="continuous",
                label="Moderate health anxiety",
                source="anchored",
            ),
            "information_need": Attribute(
                value=0.60,
                type="continuous",
                label="Moderate information need",
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
                value=0.72,
                type="continuous",
                label="High social proof sensitivity",
                source="anchored",
            ),
            "authority_bias": Attribute(
                value=0.40,
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
                value=0.28,
                type="continuous",
                label="Low ad receptivity",
                source="anchored",
            ),
            "digital_payment_comfort": Attribute(
                value=0.85,
                type="continuous",
                label="High digital payment comfort",
                source="anchored",
            ),
        },
        "identity": {
            "life_stage_priority": Attribute(
                value="career-growth",
                type="categorical",
                label="Career growth priority",
                source="anchored",
            ),
            "tension_seed": Attribute(
                value="aspiration_vs_constraint",
                type="categorical",
                label="Aspiration vs professional credibility tension",
                source="anchored",
            ),
        },
    }

    # --- Derived Insights ---
    derived_insights = DerivedInsights(
        decision_style="social",
        decision_style_score=0.68,
        trust_anchor="peer",
        risk_appetite="low",
        primary_value_orientation="quality",
        coping_mechanism=CopingMechanism(
            type="social_validation",
            description=(
                "Ritu validates decisions by polling respected peers and colleagues "
                "before committing, especially for visible or professionally relevant purchases."
            ),
        ),
        consistency_score=74,
        consistency_band="high",
        key_tensions=[
            "Aspires to quality products but is wary of unvalidated premium claims.",
            "Professional reputation is tied to recommendations, raising stakes for every purchase.",
        ],
    )

    # --- Behavioural Tendencies ---
    # TR4: social_proof_bias=0.72 → trust_weights.peer=0.72 >=0.65 ✓
    # TR6: ad_receptivity=0.28 → trust_weights.ad=0.20 <=0.25 ✓
    behavioural_tendencies = BehaviouralTendencies(
        price_sensitivity=PriceSensitivityBand(
            band="medium",
            description=(
                "Ritu compares prices but is willing to pay more when peer-endorsed "
                "quality justifies it."
            ),
            source="grounded",
        ),
        trust_orientation=TrustOrientation(
            weights=TrustWeights(
                expert=0.50,
                peer=0.72,
                brand=0.40,
                ad=0.20,
                community=0.60,
                influencer=0.35,
            ),
            dominant="peer",
            description=(
                "Colleague and peer word-of-mouth dominate Ritu's trust hierarchy. "
                "Professional credibility amplifies her reliance on vetted social signals."
            ),
            source="grounded",
        ),
        switching_propensity=TendencyBand(
            band="medium",
            description=(
                "Willing to switch when peers report clearly superior alternatives, "
                "but not an impulsive adopter."
            ),
            source="grounded",
        ),
        objection_profile=[
            Objection(
                objection_type="social_proof_gap",
                likelihood="high",
                severity="friction",
            ),
            Objection(
                objection_type="price_vs_value",
                likelihood="medium",
                severity="friction",
            ),
            Objection(
                objection_type="trust_deficit",
                likelihood="medium",
                severity="friction",
            ),
        ],
        reasoning_prompt=(
            "Ritu Sharma is a 31-year-old marketing professional in Delhi without children. "
            "She evaluates purchases through a lens of professional credibility and peer trust. "
            "Quality matters more than price, but only when validated by colleagues she respects. "
            "Her career identity means she is cautious about what she endorses or adopts, "
            "and she will not commit to a product without social proof from a trusted network. "
            "She is aspirational but pragmatic, and her tension is between wanting premium "
            "experiences and needing confidence that the quality is real."
        ),
    )

    # --- Narrative ---
    first_person = (
        "I am Ritu Sharma, a marketing professional in Delhi. I have spent years "
        "helping brands connect with consumers, which means I am deeply sceptical of "
        "brand promises unless people I trust have experienced them firsthand. I do not "
        "need to spend the least — I need to spend wisely and be confident in what I "
        "recommend or use. My colleagues and friends are my real review system. Before "
        "I adopt anything new, I listen to what people whose judgment I respect have "
        "experienced. My professional reputation has taught me that unchecked optimism "
        "about new products can embarrass you publicly."
    )

    third_person = (
        "Ritu Sharma is a 31-year-old marketing professional living in Delhi with her "
        "partner in a dual-income household. Without children, her consumption priorities "
        "centre on professional identity, quality of life, and social credibility rather "
        "than family safety. Her decision style is strongly social: she relies on "
        "colleague and peer testimony before adopting new products, treating her "
        "professional network as a more reliable signal than advertising or brand authority. "
        "She has moderate price sensitivity — willing to spend more for peer-endorsed "
        "quality but resistant to premium claims without social validation. Her career "
        "in marketing has made her acutely aware of brand manipulation, heightening her "
        "scepticism and elevating peer trust above all other signals. She applies "
        "consistent evaluation criteria across categories and rarely acts without "
        "confirmation from trusted peers."
    )

    narrative = Narrative(
        first_person=first_person,
        third_person=third_person,
        display_name="Ritu S.",
    )

    # --- Core Memory ---
    core_memory = CoreMemory(
        identity_statement=(
            "I am a marketing professional in Delhi who validates every "
            "significant purchase through trusted peers before committing, "
            "protecting both my wallet and professional reputation."
        ),
        key_values=[
            "Professional credibility anchors every product decision",
            "Peer-validated quality over premium marketing claims",
            "Social proof is the most reliable filter",
            "Reputation is harder to rebuild than savings",
        ],
        life_defining_events=[
            LifeDefiningEvent(
                age_when=25,
                event="Recommended a product publicly based on advertising; it failed.",
                lasting_impact="Professional reputation requires peer-vetted decisions.",
            ),
            LifeDefiningEvent(
                age_when=28,
                event="Colleague recommendation introduced a new brand that became a staple.",
                lasting_impact="Trusted peer testimony breaks adoption barriers faster than marketing.",
            ),
        ],
        relationship_map=RelationshipMap(
            primary_decision_partner="partner",
            key_influencers=["peer network", "professional colleagues"],
            trust_network=["colleagues", "close friends", "respected peers"],
        ),
        immutable_constraints=ImmutableConstraints(
            budget_ceiling="upper-middle dual income, no dependents",
            non_negotiables=[
                "Must manage: quality claims without peer validation are distrusted",
                "Must manage: professional reputation risk on any public endorsement",
            ],
            absolute_avoidances=[],
        ),
        tendency_summary=(
            "Ritu applies a peer-first, quality-second filter to all significant purchases. "
            "She distrusts advertising and premium brand claims unless backed by trusted "
            "colleague or peer testimony. Her marketing background heightens scepticism. "
            "Without children, her priorities are career identity and social credibility "
            "rather than family safety, creating different tensions to budget-focused peers."
        ),
    )

    # --- Working Memory ---
    working_memory = bootstrap_seed_memories(
        core_memory=core_memory,
        persona_name="Ritu Sharma",
    )

    # --- Decision Bullets ---
    decision_bullets = [
        "Social decision style (score: 0.68) — peer opinion from professionals drives final call",
        "Quality orientation: will pay premium only with peer validation",
        "Risk appetite: low — avoids unvalidated products to protect reputation",
        "Medium price sensitivity: quality over cost when social proof is present",
        "Objection triggers: social proof gap, price-vs-value, trust deficit",
    ]

    # --- Assemble PersonaRecord ---
    persona = PersonaRecord(
        persona_id="pg-ritu-001",
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
        f"_make_adjacent_persona() produced a persona that failed validation: {failures}"
    )

    return persona


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_survey_pipeline_completes():
    """5 personas × 5 questions → 25 responses + 5-question report."""
    personas = [make_synthetic_persona() for _ in range(5)]
    result = await run_survey(SURVEY_QUESTIONS, personas)

    assert len(result.responses) == 25
    assert len(result.questions) == 5

    report = generate_report(result)
    assert len(report.question_summaries) == 5
    assert report.cohort_size == 5


@pytest.mark.asyncio
@pytest.mark.integration
async def test_bv4_responses_reference_persona_identity():
    """
    BV4: >= 3/5 responses should reference persona-specific signals.
    Check: reasoning_trace length >= 100 chars AND contains at least one
    identity word from Priya's profile.
    """
    persona = make_synthetic_persona()
    result = await run_survey(SURVEY_QUESTIONS, [persona])

    identity_signals = ['budget', 'family', 'quality', 'price', 'children',
                        'trust', 'peer', 'expensive', 'priya', 'mehta']
    persona_responses = [r for r in result.responses if r.persona_id == persona.persona_id]

    grounded = sum(
        1 for r in persona_responses
        if len(r.reasoning_trace) >= 100
        and any(w in r.reasoning_trace.lower() for w in identity_signals)
    )
    assert grounded >= 3, f"BV4 FAIL: {grounded}/5 responses grounded"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_bv5_adjacent_personas_produce_distinct_responses():
    """
    BV5: Two similar personas produce < 50% shared language (Jaccard) on >= 3/5 questions.
    """
    persona_a = make_synthetic_persona()
    persona_b = _make_adjacent_persona()

    result = await run_survey(SURVEY_QUESTIONS, [persona_a, persona_b])

    resp_a = {r.question_id: r for r in result.responses if r.persona_id == persona_a.persona_id}
    resp_b = {r.question_id: r for r in result.responses if r.persona_id == persona_b.persona_id}

    distinct_count = 0
    for q in SURVEY_QUESTIONS:
        words_a = set(resp_a[q.id].reasoning_trace.lower().split())
        words_b = set(resp_b[q.id].reasoning_trace.lower().split())
        if words_a | words_b:
            jaccard = len(words_a & words_b) / len(words_a | words_b)
            if jaccard < 0.50:
                distinct_count += 1

    assert distinct_count >= 3, f"BV5 FAIL: only {distinct_count}/5 questions distinct"
