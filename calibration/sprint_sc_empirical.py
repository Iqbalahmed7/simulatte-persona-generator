"""Sprint SC — Empirical Validation: SVB1, SVB2, SVB3

Run: python3 calibration/sprint_sc_empirical.py

Validates the susceptibility formula, signal strength distribution,
and echo chamber baseline across synthetic persona archetypes.

No LLM. All deterministic.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timezone
from itertools import product

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
    Reflection,
    RelationshipMap,
    SimulationState,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
    WorkingMemory,
)
from src.social.influence_engine import (
    compute_gated_importance,
    compute_signal_strength,
    compute_susceptibility,
    generate_influence_events,
)
from src.social.network_builder import build_full_mesh, build_random_encounter
from src.social.schema import (
    NetworkTopology,
    SocialNetwork,
    SocialSimulationLevel,
)


# ---------------------------------------------------------------------------
# Fixture factory
# ---------------------------------------------------------------------------

def make_persona(
    persona_id: str,
    peer_weight: float,
    social_proof_bias: float,
    wom_receiver_openness: float,
    consistency_score: int,
    decision_style: str,
    decision_style_score: float,
) -> PersonaRecord:
    """Build a synthetic PersonaRecord for calibration."""
    remaining = max(0.0, 1.0 - peer_weight - 0.1 - 0.05 - 0.05)
    expert_w = remaining * 0.7
    brand_w = 0.1
    ad_w = 0.05
    community_w = remaining * 0.3
    influencer_w = 0.05

    return PersonaRecord(
        persona_id=persona_id,
        generated_at=datetime.now(timezone.utc),
        generator_version="sc-calibration",
        domain="cpg",
        mode="quick",
        demographic_anchor=DemographicAnchor(
            name=f"Persona {persona_id}",
            age=30,
            gender="female",
            location=Location(country="India", region="MH", city="Mumbai", urban_tier="metro"),
            household=Household(structure="nuclear", size=4, income_bracket="middle", dual_income=True),
            life_stage="adult",
            education="undergraduate",
            employment="full-time",
        ),
        life_stories=[
            LifeStory(title="A", when="2020", event="Event A", lasting_impact="Impact A"),
            LifeStory(title="B", when="2018", event="Event B", lasting_impact="Impact B"),
        ],
        attributes={
            "base": {"openness": Attribute(value=0.7, type="continuous", label="Openness", source="sampled")},
            "social": {
                "social_proof_bias": Attribute(value=social_proof_bias, type="continuous", label="Social proof bias", source="sampled"),
                "wom_receiver_openness": Attribute(value=wom_receiver_openness, type="continuous", label="WOM openness", source="sampled"),
            },
        },
        derived_insights=DerivedInsights(
            decision_style=decision_style,
            decision_style_score=decision_style_score,
            trust_anchor="authority",
            risk_appetite="medium",
            primary_value_orientation="quality",
            coping_mechanism=CopingMechanism(type="research_deep_dive", description="Researches deeply"),
            consistency_score=consistency_score,
            consistency_band="high" if consistency_score >= 70 else "medium",
            key_tensions=["price vs quality"],
        ),
        behavioural_tendencies=BehaviouralTendencies(
            price_sensitivity=PriceSensitivityBand(band="medium", description="moderate", source="grounded"),
            trust_orientation=TrustOrientation(
                weights=TrustWeights(
                    expert=round(expert_w, 4),
                    peer=peer_weight,
                    brand=brand_w,
                    ad=ad_w,
                    community=round(community_w, 4),
                    influencer=influencer_w,
                ),
                dominant="expert",
                description="trusts experts",
                source="grounded",
            ),
            switching_propensity=TendencyBand(band="low", description="loyal", source="grounded"),
            objection_profile=[
                Objection(objection_type="price_vs_value", likelihood="medium", severity="friction")
            ],
            reasoning_prompt="Think carefully.",
        ),
        narrative=Narrative(first_person="I am...", third_person="She is...", display_name="Test"),
        decision_bullets=["Quality first"],
        memory=Memory(
            core=CoreMemory(
                identity_statement="A careful thinker",
                key_values=["quality", "trust", "value"],
                life_defining_events=[
                    LifeDefiningEvent(age_when=25, event="Career start", lasting_impact="Ambition")
                ],
                relationship_map=RelationshipMap(
                    primary_decision_partner="spouse",
                    key_influencers=["doctor"],
                    trust_network=["family"],
                ),
                immutable_constraints=ImmutableConstraints(
                    budget_ceiling=None,
                    non_negotiables=["quality"],
                    absolute_avoidances=["fake"],
                ),
                tendency_summary="Careful",
            ),
            working=WorkingMemory(
                observations=[],
                reflections=[],
                plans=[],
                brand_memories={},
                simulation_state=SimulationState(
                    current_turn=0,
                    importance_accumulator=0.0,
                    reflection_count=0,
                    awareness_set={},
                    consideration_set=[],
                    last_decision=None,
                ),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# SVB1 — Susceptibility calibration
# ---------------------------------------------------------------------------

def run_svb1() -> dict:
    """Run susceptibility formula across 3*3*3*3*3 = 243 synthetic archetypes."""
    peer_weights = [0.05, 0.30, 0.60]
    spb_values = [0.1, 0.5, 0.9]       # social_proof_bias
    wom_values = [0.1, 0.5, 0.9]       # wom_receiver_openness
    cs_values = [20, 60, 90]           # consistency_score
    styles = ["analytical", "habitual", "social"]

    scores = []
    for i, (pw, spb, wom, cs, style) in enumerate(
        product(peer_weights, spb_values, wom_values, cs_values, styles)
    ):
        p = make_persona(
            persona_id=f"svb1-{i:04d}",
            peer_weight=pw,
            social_proof_bias=spb,
            wom_receiver_openness=wom,
            consistency_score=cs,
            decision_style=style,
            decision_style_score=0.7,
        )
        scores.append(compute_susceptibility(p))

    return {
        "n": len(scores),
        "min": round(min(scores), 4),
        "max": round(max(scores), 4),
        "mean": round(statistics.mean(scores), 4),
        "median": round(statistics.median(scores), 4),
        "stdev": round(statistics.stdev(scores), 4),
        "pct10": round(sorted(scores)[len(scores) // 10], 4),
        "pct90": round(sorted(scores)[9 * len(scores) // 10], 4),
        "clamped_at_0": sum(1 for s in scores if s <= 0.0),
        "clamped_at_1": sum(1 for s in scores if s >= 1.0),
    }


# ---------------------------------------------------------------------------
# SVB2 — Signal strength distribution
# ---------------------------------------------------------------------------

def run_svb2() -> dict:
    """Run signal strength formula across 5*5 = 25 archetypes."""
    dss_values = [0.1, 0.3, 0.5, 0.7, 0.9]
    cs_values = [10, 30, 55, 75, 95]

    scores = []
    for i, (dss, cs) in enumerate(product(dss_values, cs_values)):
        p = make_persona(
            persona_id=f"svb2-{i:04d}",
            peer_weight=0.2,
            social_proof_bias=0.5,
            wom_receiver_openness=0.5,
            consistency_score=cs,
            decision_style="habitual",
            decision_style_score=dss,
        )
        scores.append(compute_signal_strength(p))

    return {
        "n": len(scores),
        "min": round(min(scores), 4),
        "max": round(max(scores), 4),
        "mean": round(statistics.mean(scores), 4),
        "stdev": round(statistics.stdev(scores), 4),
    }


# ---------------------------------------------------------------------------
# SVB3 — Echo chamber baseline by topology + cohort size
# ---------------------------------------------------------------------------

def run_svb3() -> dict:
    """Compute echo chamber scores for FULL_MESH and RANDOM_ENCOUNTER at N=2,3,4,6."""
    from collections import Counter

    results = []
    cohort_sizes = [2, 3, 4, 6]

    for n in cohort_sizes:
        personas = [
            make_persona(f"svb3-{n}-{i}", 0.2, 0.5, 0.5, 60, "habitual", 0.7)
            for i in range(n)
        ]

        persona_ids = [p.persona_id for p in personas]

        # FULL_MESH
        net = build_full_mesh(persona_ids)
        tx_counts = Counter(e.source_id for e in net.edges)
        max_count = max(tx_counts.values()) if tx_counts else 0
        total = len(net.edges)
        score_fm = max_count / total if total > 0 else 0.0

        # RANDOM_ENCOUNTER (seed=42)
        net_re = build_random_encounter(persona_ids, k=min(2, n - 1), seed=42)
        tx_counts_re = Counter(e.source_id for e in net_re.edges)
        max_count_re = max(tx_counts_re.values()) if tx_counts_re else 0
        total_re = len(net_re.edges)
        score_re = max_count_re / total_re if total_re > 0 else 0.0

        results.append({
            "n": n,
            "full_mesh_edges": total,
            "full_mesh_echo_score": round(score_fm, 4),
            "full_mesh_sv3_zone": "FAIL" if score_fm > 0.80 else ("WARN" if score_fm > 0.60 else "PASS"),
            "random_encounter_edges": total_re,
            "random_encounter_echo_score": round(score_re, 4),
            "random_encounter_sv3_zone": "FAIL" if score_re > 0.80 else ("WARN" if score_re > 0.60 else "PASS"),
        })

    return {"cohort_scenarios": results}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("SPRINT SC — EMPIRICAL VALIDATION")
    print("=" * 60)

    print("\n--- SVB1: Susceptibility Distribution (N=243) ---")
    svb1 = run_svb1()
    for k, v in svb1.items():
        print(f"  {k}: {v}")

    print("\n--- SVB2: Signal Strength Distribution (N=25) ---")
    svb2 = run_svb2()
    for k, v in svb2.items():
        print(f"  {k}: {v}")

    print("\n--- SVB3: Echo Chamber Baseline ---")
    svb3 = run_svb3()
    for row in svb3["cohort_scenarios"]:
        print(f"  N={row['n']}: FM={row['full_mesh_echo_score']} ({row['full_mesh_sv3_zone']}) | "
              f"RE={row['random_encounter_echo_score']} ({row['random_encounter_sv3_zone']})")

    results = {"svb1": svb1, "svb2": svb2, "svb3": svb3}
    out_path = "calibration/sprint_sc_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")
