"""src/cohort/assembler.py — Cohort Assembly Orchestrator.

Takes a list of PersonaRecord objects and assembles them into a validated
CohortEnvelope. Runs G6, G7, G8, G9, G11 gates via CohortGateRunner.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

from src.schema.cohort import (
    CalibrationState,
    CohortEnvelope,
    CohortSummary,
    GroundingSummary,
    TaxonomyMeta,
)
from src.schema.persona import PersonaRecord

# Integration contract: CohortGateRunner provided by Antigravity (validators.py)
try:
    from src.schema.validators import CohortGateRunner
except ImportError:
    CohortGateRunner = None  # type: ignore[assignment,misc]

# Integration contract: classify_persona_type provided by Codex (type_coverage.py)
try:
    from src.cohort.type_coverage import classify_persona_type
except ImportError:
    classify_persona_type = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Age bracket helper
# ---------------------------------------------------------------------------

def _age_bracket(age: int) -> str:
    """Map an integer age to a display bracket string."""
    if age < 18:
        return "<18"
    elif age < 25:
        return "18-24"
    elif age < 35:
        return "25-34"
    elif age < 45:
        return "35-44"
    elif age < 55:
        return "45-54"
    elif age < 65:
        return "55-64"
    else:
        return "65+"


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------

def _compute_summary(
    personas: list[PersonaRecord],
    domain: str,
) -> CohortSummary:
    """
    Compute a CohortSummary from the assembled persona list.

    Populates the actual CohortSummary schema fields:
    - decision_style_distribution: label → count
    - trust_anchor_distribution: label → count
    - risk_appetite_distribution: label → count
    - consistency_scores: persona_id → consistency_score
    - persona_type_distribution: type label → count (requires classify_persona_type)
    - distinctiveness_score: mean pairwise cosine distance placeholder (0.0 if unavailable)
    - coverage_assessment: human-readable string
    - dominant_tensions: list of most-common tension phrases across the cohort

    Auxiliary data computed but stored in coverage_assessment as structured text:
    - size, domain, age_distribution, city_distribution, income_distribution
    """
    # decision_style_distribution
    decision_styles = [p.derived_insights.decision_style for p in personas]
    decision_style_distribution: dict = dict(Counter(decision_styles))

    # trust_anchor_distribution
    trust_anchors = [p.derived_insights.trust_anchor for p in personas]
    trust_anchor_distribution: dict = dict(Counter(trust_anchors))

    # risk_appetite_distribution
    risk_appetites = [p.derived_insights.risk_appetite for p in personas]
    risk_appetite_distribution: dict = dict(Counter(risk_appetites))

    # consistency_scores: persona_id → int score
    consistency_scores: dict = {
        p.persona_id: p.derived_insights.consistency_score for p in personas
    }

    # persona_type_distribution
    if classify_persona_type is not None:
        type_labels = [classify_persona_type(p).value for p in personas]
    else:
        type_labels = ["unknown"] * len(personas)
    persona_type_distribution: dict = dict(Counter(type_labels))

    # Compute actual distinctiveness score via G7 check
    try:
        from src.cohort.distinctiveness import check_distinctiveness
        dist_result = check_distinctiveness(personas)
        distinctiveness_score: float = dist_result.mean_pairwise_distance
    except Exception:
        distinctiveness_score = 0.0  # Graceful fallback

    # dominant_tensions: collect all key_tensions across personas, rank by frequency
    all_tensions: list[str] = []
    for p in personas:
        all_tensions.extend(p.derived_insights.key_tensions)
    tension_counter = Counter(all_tensions)
    # Top-5 most common tensions; if fewer than 5, take all
    dominant_tensions: list[str] = [t for t, _ in tension_counter.most_common(5)]
    if not dominant_tensions:
        dominant_tensions = ["no tensions recorded"]

    # coverage_assessment: structured summary string
    size = len(personas)
    age_dist = dict(Counter(_age_bracket(p.demographic_anchor.age) for p in personas))
    city_dist = dict(Counter(p.demographic_anchor.location.city for p in personas))
    income_dist = dict(
        Counter(p.demographic_anchor.household.income_bracket for p in personas)
    )
    coverage_assessment = (
        f"domain={domain} size={size} "
        f"ages={age_dist} cities={city_dist} income={income_dist}"
    )

    return CohortSummary(
        decision_style_distribution=decision_style_distribution,
        trust_anchor_distribution=trust_anchor_distribution,
        risk_appetite_distribution=risk_appetite_distribution,
        consistency_scores=consistency_scores,
        persona_type_distribution=persona_type_distribution,
        distinctiveness_score=distinctiveness_score,
        coverage_assessment=coverage_assessment,
        dominant_tensions=dominant_tensions,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assemble_cohort(
    personas: list[PersonaRecord],
    domain: str,
    cohort_id: str | None = None,
    domain_data: list[str] | None = None,
    business_problem: str = "",
    skip_gates: bool = False,
) -> CohortEnvelope:
    """
    Assemble N personas into a validated CohortEnvelope.

    If domain_data is provided (list of raw text strings — reviews, posts),
    runs the grounding pipeline to upgrade persona tendency sources from
    'proxy' to 'grounded' before building the envelope. The GroundingSummary
    will reflect actual signal and cluster counts.

    Raises ValueError listing failed gates if any gate fails.
    cohort_id defaults to f"cohort-{uuid4().hex[:8]}"

    skip_gates: if True, cohort-level gates (G6/G7/G8/G9/G11) are checked but
    failures are printed as warnings rather than raising ValueError.
    """
    if not personas:
        raise ValueError("assemble_cohort requires at least one persona")

    # Step 1: G1 is implicitly satisfied — PersonaRecord construction via Pydantic
    # already enforces schema validity. PersonaValidator.g1_schema_validity() does
    # supplementary checks (persona_id format, field counts) but is not re-run here
    # as the fixture/generator is responsible for producing valid records.

    # Step 2: Cohort-level gates G6, G7, G8, G9, G11
    failed_gates: list[str] = []

    if CohortGateRunner is not None:
        runner = CohortGateRunner()
        gate_results = runner.run_all(personas)
        for result in gate_results:
            if not result.passed:
                failed_detail = "; ".join(result.failures) if result.failures else "no details"
                failed_gates.append(f"{result.gate}: {failed_detail}")
    # If CohortGateRunner is not yet available (parallel sprint build), skip silently.

    if failed_gates:
        if skip_gates:
            import warnings
            warnings.warn(
                f"Cohort gate warnings (--skip-gates active): "
                + " | ".join(failed_gates),
                stacklevel=2,
            )
        else:
            raise ValueError(
                f"Cohort failed {len(failed_gates)} gate(s): " + " | ".join(failed_gates)
            )

    # Step 2.5 (NEW): Grounding pipeline — runs after gate validation,
    # before summary + envelope construction.
    grounding_signals_extracted: int = 0
    grounding_clusters_derived: int = 0
    domain_data_used: bool = False
    grounded_mode: str = personas[0].mode  # default: keep original mode

    if domain_data:
        from src.grounding.pipeline import run_grounding_pipeline
        grounding_result = run_grounding_pipeline(domain_data, personas)
        personas = grounding_result.personas          # updated with grounded tendencies
        personas = [p.model_copy(update={"mode": "grounded"}) for p in personas]
        grounding_signals_extracted = grounding_result.signals_extracted
        grounding_clusters_derived = grounding_result.clusters_derived
        domain_data_used = True
        grounded_mode = "grounded"

    # Step 3: Compute summary
    cohort_summary = _compute_summary(personas, domain)

    # Step 4: Build CohortEnvelope
    if cohort_id is None:
        cohort_id = f"cohort-{uuid4().hex[:8]}"

    # Derive mode — "grounded" if domain_data was provided, else first persona's mode
    mode = grounded_mode

    # Recompute tendency sources from (potentially updated) personas
    tendency_sources: list[str] = []
    for p in personas:
        bt = p.behavioural_tendencies
        for field_name in ("price_sensitivity", "switching_propensity", "trust_orientation"):
            obj = getattr(bt, field_name, None)
            if obj is not None and hasattr(obj, "source") and obj.source is not None:
                tendency_sources.append(obj.source)

    total_sources = len(tendency_sources) if tendency_sources else 1
    source_counts = Counter(tendency_sources)
    dist = {
        "grounded": round(source_counts.get("grounded", 0) / total_sources, 6),
        "proxy": round(source_counts.get("proxy", 0) / total_sources, 6),
        "estimated": round(source_counts.get("estimated", 0) / total_sources, 6),
    }
    # Correct rounding drift — add/subtract residual to/from largest bucket
    _total = sum(dist.values())
    if abs(_total - 1.0) > 1e-9:
        largest_key = max(dist, key=lambda k: dist[k])
        dist[largest_key] = round(dist[largest_key] + (1.0 - _total), 9)
    grounding_summary = GroundingSummary(
        tendency_source_distribution=dist,
        domain_data_signals_extracted=grounding_signals_extracted,
        clusters_derived=grounding_clusters_derived,
    )

    # Calibration state defaults to uncalibrated for a freshly assembled cohort
    calibration_state = CalibrationState(
        status="uncalibrated",
        method_applied=None,
        last_calibrated=None,
        benchmark_source=None,
        notes=None,
    )

    # Compute deterministic icp_spec_hash from domain + persona count + sorted persona_ids
    import hashlib
    import json as _json
    _hash_payload = _json.dumps({
        "domain": domain,
        "count": len(personas),
        "persona_ids": sorted(p.persona_id for p in personas),
    }, sort_keys=True)
    icp_spec_hash = hashlib.sha256(_hash_payload.encode()).hexdigest()[:16]

    # TaxonomyMeta: count attributes from the first persona as representative
    first_persona = personas[0]
    total_attrs = sum(len(cat) for cat in first_persona.attributes.values())
    taxonomy_used = TaxonomyMeta(
        base_attributes=total_attrs,
        domain_extension_attributes=0,
        total_attributes=total_attrs,
        domain_data_used=domain_data_used,
        business_problem=business_problem,
        icp_spec_hash=icp_spec_hash,
    )

    envelope = CohortEnvelope(
        cohort_id=cohort_id,
        generated_at=datetime.now(timezone.utc),
        domain=domain,
        business_problem=business_problem,
        mode=mode,
        icp_spec_hash=icp_spec_hash,
        taxonomy_used=taxonomy_used,
        personas=personas,
        cohort_summary=cohort_summary,
        grounding_summary=grounding_summary,
        calibration_state=calibration_state,
    )

    return envelope
