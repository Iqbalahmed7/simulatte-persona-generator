"""Persona Quality Score (PQS) — composite quality metric.

Combines four dimensions into a single 0–100 score per cohort:
  1. Behavioral Realism  (BV6-style consistency + override presence)
  2. Identity Depth      (narrative, life stories, memory, tensions)
  3. Decision Quality    (constraint awareness, semantic grounding, reasoning depth)
  4. Cohort Health       (distinctiveness, type coverage, distribution)

Usage:
    from src.quality.pqs import compute_pqs, PQSReport
    report = compute_pqs(envelope)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class DimensionScore:
    """Score for one PQS dimension."""
    name: str
    score: float          # 0.0–1.0
    weight: float         # 0.0–1.0, sums to 1.0 across all dimensions
    components: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class PQSReport:
    """Complete PQS result for a cohort."""
    pqs: float                         # 0–100 composite
    dimensions: list[DimensionScore]   # 4 dimension breakdowns
    persona_scores: dict[str, float]   # per-persona PQS (0–100)
    cohort_id: str = ""
    domain: str = ""
    persona_count: int = 0


# ---------------------------------------------------------------------------
# Dimension 1: Behavioral Realism (0.0–1.0)
# ---------------------------------------------------------------------------

def _behavioral_realism(personas: list[Any]) -> DimensionScore:
    """Measures whether personas behave realistically (not too consistent,
    not too random).

    Components:
      - consistency_band_diversity: Are personas spread across low/med/high?
      - tension_presence:          Does every persona have ≥1 tension?
      - noise_presence:            Does DecisionOutput.noise_applied exist?
    """
    components: dict[str, float] = {}
    notes: list[str] = []

    # Consistency band diversity (want spread, not all "high")
    bands = {"low": 0, "medium": 0, "high": 0}
    tension_count = 0
    total = len(personas)

    for p in personas:
        di = p.derived_insights
        band = getattr(di, "consistency_band", "medium")
        if band in bands:
            bands[band] += 1

        tensions = getattr(di, "key_tensions", [])
        if tensions and len(tensions) >= 1:
            tension_count += 1

    # Band diversity: Shannon entropy normalized (max when equal distribution)
    band_counts = [v for v in bands.values() if v > 0]
    if band_counts and total > 0:
        probs = [c / total for c in band_counts]
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        max_entropy = math.log2(len(bands))  # log2(3) ≈ 1.585
        band_diversity = entropy / max_entropy if max_entropy > 0 else 0.0
    else:
        band_diversity = 0.0

    components["consistency_band_diversity"] = round(band_diversity, 3)

    # Tension presence: fraction with ≥1 tension
    tension_rate = tension_count / total if total > 0 else 0.0
    components["tension_presence"] = round(tension_rate, 3)

    if band_diversity < 0.5:
        notes.append(f"Low band diversity ({band_diversity:.2f}) — personas are too similar in consistency")

    score = 0.5 * band_diversity + 0.5 * tension_rate

    return DimensionScore(
        name="Behavioral Realism",
        score=round(min(1.0, score), 3),
        weight=0.25,
        components=components,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Dimension 2: Identity Depth (0.0–1.0)
# ---------------------------------------------------------------------------

def _identity_depth(personas: list[Any]) -> DimensionScore:
    """Measures richness of persona identity.

    Components:
      - narrative_completeness:  first_person + third_person present and ≥80 words each
      - life_story_count:        avg life stories per persona (target: 2-3)
      - memory_seed_count:       avg seed memories (core.life_defining_events)
      - relationship_completeness: has primary_decision_partner + ≥1 influencer
    """
    components: dict[str, float] = {}
    notes: list[str] = []
    total = len(personas)

    narrative_scores = []
    life_story_scores = []
    memory_scores = []
    relationship_scores = []

    for p in personas:
        # Narrative completeness
        narr = p.narrative
        fp = getattr(narr, "first_person", "") or ""
        tp = getattr(narr, "third_person", "") or ""
        fp_ok = len(fp.split()) >= 80
        tp_ok = len(tp.split()) >= 80
        narr_score = (0.5 if fp_ok else len(fp.split()) / 160.0) + \
                     (0.5 if tp_ok else len(tp.split()) / 160.0)
        narrative_scores.append(min(1.0, narr_score))

        # Life stories
        stories = getattr(p, "life_stories", []) or []
        ls_score = min(1.0, len(stories) / 2.5)  # 2.5 = midpoint of target 2-3
        life_story_scores.append(ls_score)

        # Memory seeds
        core = p.memory.core
        events = getattr(core, "life_defining_events", []) or []
        mem_score = min(1.0, len(events) / 3.0)
        memory_scores.append(mem_score)

        # Relationship map completeness
        rel = getattr(core, "relationship_map", None)
        rel_score = 0.0
        if rel:
            has_partner = bool(getattr(rel, "primary_decision_partner", ""))
            has_influencers = len(getattr(rel, "key_influencers", []) or []) >= 1
            rel_score = (0.5 if has_partner else 0.0) + (0.5 if has_influencers else 0.0)
        relationship_scores.append(rel_score)

    avg = lambda lst: sum(lst) / len(lst) if lst else 0.0

    components["narrative_completeness"] = round(avg(narrative_scores), 3)
    components["life_story_depth"] = round(avg(life_story_scores), 3)
    components["memory_seed_depth"] = round(avg(memory_scores), 3)
    components["relationship_completeness"] = round(avg(relationship_scores), 3)

    score = (
        0.30 * components["narrative_completeness"]
        + 0.25 * components["life_story_depth"]
        + 0.25 * components["memory_seed_depth"]
        + 0.20 * components["relationship_completeness"]
    )

    return DimensionScore(
        name="Identity Depth",
        score=round(min(1.0, score), 3),
        weight=0.25,
        components=components,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Dimension 3: Decision Quality (0.0–1.0)
# ---------------------------------------------------------------------------

def _decision_quality(personas: list[Any]) -> DimensionScore:
    """Measures structural quality of decision-relevant fields.

    Components:
      - tendency_source_coverage:  fraction with source != "estimated"
      - objection_profile_depth:   avg objection count per persona
      - decision_bullet_count:     avg decision bullets (target: 3-5)
      - constraint_completeness:   has budget_ceiling + non_negotiables + avoidances
    """
    components: dict[str, float] = {}
    notes: list[str] = []
    total = len(personas)

    source_scores = []
    objection_scores = []
    bullet_scores = []
    constraint_scores = []

    for p in personas:
        bt = p.behavioural_tendencies

        # Tendency source coverage
        source_count = 0
        total_tendencies = 0
        for field_name in ("price_sensitivity", "trust_orientation", "switching_propensity"):
            tendency = getattr(bt, field_name, None)
            if tendency is not None:
                total_tendencies += 1
                src = getattr(tendency, "source", "estimated")
                if src in ("grounded", "proxy"):
                    source_count += 1
        source_scores.append(source_count / max(1, total_tendencies))

        # Objection profile depth
        obj_profile = getattr(bt, "objection_profile", []) or []
        obj_score = min(1.0, len(obj_profile) / 2.0)  # target: ≥2
        objection_scores.append(obj_score)

        # Decision bullets
        bullets = getattr(p, "decision_bullets", []) or []
        b_score = min(1.0, len(bullets) / 4.0)  # target: 4
        bullet_scores.append(b_score)

        # Constraint completeness
        constraints = getattr(p.memory.core, "immutable_constraints", None)
        c_score = 0.0
        if constraints:
            has_budget = bool(getattr(constraints, "budget_ceiling", None))
            has_nn = len(getattr(constraints, "non_negotiables", []) or []) >= 1
            has_avoid = len(getattr(constraints, "absolute_avoidances", []) or []) >= 1
            c_score = sum([has_budget, has_nn, has_avoid]) / 3.0
        constraint_scores.append(c_score)

    avg = lambda lst: sum(lst) / len(lst) if lst else 0.0

    components["tendency_source_coverage"] = round(avg(source_scores), 3)
    components["objection_profile_depth"] = round(avg(objection_scores), 3)
    components["decision_bullet_count"] = round(avg(bullet_scores), 3)
    components["constraint_completeness"] = round(avg(constraint_scores), 3)

    score = (
        0.30 * components["tendency_source_coverage"]
        + 0.25 * components["objection_profile_depth"]
        + 0.20 * components["decision_bullet_count"]
        + 0.25 * components["constraint_completeness"]
    )

    return DimensionScore(
        name="Decision Quality",
        score=round(min(1.0, score), 3),
        weight=0.25,
        components=components,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Dimension 4: Cohort Health (0.0–1.0)
# ---------------------------------------------------------------------------

def _cohort_health(envelope: Any) -> DimensionScore:
    """Measures diversity and representativeness of the cohort.

    Components:
      - distinctiveness_score:       from cohort_summary
      - type_coverage:               unique persona types / 8
      - decision_style_diversity:    entropy of decision style distribution
      - trust_anchor_diversity:      entropy of trust anchor distribution
    """
    components: dict[str, float] = {}
    notes: list[str] = []

    summary = envelope.cohort_summary
    personas = envelope.personas

    # Distinctiveness score (already 0-1)
    dist_score = getattr(summary, "distinctiveness_score", 0.0)
    components["distinctiveness"] = round(dist_score, 3)

    # Type coverage
    type_dist = getattr(summary, "persona_type_distribution", {})
    if isinstance(type_dist, dict):
        unique_types = sum(1 for v in type_dist.values() if v > 0)
    else:
        unique_types = 0
    type_coverage = min(1.0, unique_types / 8.0)
    components["type_coverage"] = round(type_coverage, 3)

    # Decision style diversity (entropy)
    ds_dist = getattr(summary, "decision_style_distribution", {})
    ds_diversity = _normalized_entropy(ds_dist)
    components["decision_style_diversity"] = round(ds_diversity, 3)

    # Trust anchor diversity (entropy)
    ta_dist = getattr(summary, "trust_anchor_distribution", {})
    ta_diversity = _normalized_entropy(ta_dist)
    components["trust_anchor_diversity"] = round(ta_diversity, 3)

    if dist_score < 0.20:
        notes.append(f"Low distinctiveness ({dist_score:.2f}) — personas may be too similar")

    score = (
        0.35 * dist_score
        + 0.25 * type_coverage
        + 0.20 * ds_diversity
        + 0.20 * ta_diversity
    )

    return DimensionScore(
        name="Cohort Health",
        score=round(min(1.0, score), 3),
        weight=0.25,
        components=components,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalized_entropy(distribution: dict) -> float:
    """Shannon entropy normalized to [0, 1]."""
    if not distribution:
        return 0.0
    counts = [v for v in distribution.values() if v > 0]
    if not counts:
        return 0.0
    total = sum(counts)
    probs = [c / total for c in counts]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    max_entropy = math.log2(len(counts))
    return entropy / max_entropy if max_entropy > 0 else 0.0


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def compute_pqs(envelope: Any) -> PQSReport:
    """Compute the Persona Quality Score for a CohortEnvelope.

    Returns a PQSReport with:
      - pqs: 0–100 composite score
      - dimensions: 4 DimensionScore breakdowns
      - persona_scores: per-persona quality (0–100)
    """
    personas = envelope.personas

    dim1 = _behavioral_realism(personas)
    dim2 = _identity_depth(personas)
    dim3 = _decision_quality(personas)
    dim4 = _cohort_health(envelope)

    dimensions = [dim1, dim2, dim3, dim4]

    # Composite: weighted sum × 100
    composite = sum(d.score * d.weight for d in dimensions) * 100

    # Per-persona scores (simplified: identity depth + decision quality per persona)
    persona_scores: dict[str, float] = {}
    for p in personas:
        p_id = p.persona_id
        # Individual identity depth
        p_narr = p.narrative
        fp = getattr(p_narr, "first_person", "") or ""
        tp = getattr(p_narr, "third_person", "") or ""
        narr = min(1.0, (len(fp.split()) + len(tp.split())) / 200.0)

        stories = getattr(p, "life_stories", []) or []
        ls = min(1.0, len(stories) / 2.5)

        events = getattr(p.memory.core, "life_defining_events", []) or []
        mem = min(1.0, len(events) / 3.0)

        tensions = getattr(p.derived_insights, "key_tensions", []) or []
        ten = min(1.0, len(tensions) / 1.5)

        bullets = getattr(p, "decision_bullets", []) or []
        bul = min(1.0, len(bullets) / 4.0)

        p_score = (0.25 * narr + 0.20 * ls + 0.20 * mem + 0.15 * ten + 0.20 * bul) * 100
        persona_scores[p_id] = round(p_score, 1)

    return PQSReport(
        pqs=round(composite, 1),
        dimensions=dimensions,
        persona_scores=persona_scores,
        cohort_id=getattr(envelope, "cohort_id", ""),
        domain=getattr(envelope, "domain", ""),
        persona_count=len(personas),
    )


def format_pqs_report(report: PQSReport) -> str:
    """Format a PQSReport as human-readable text."""
    lines = [
        "╔══════════════════════════════════════════════════════════════╗",
        f"║  PERSONA QUALITY SCORE (PQS)           {report.pqs:>5.1f} / 100          ║",
        f"║  Cohort: {report.cohort_id:<30s} N={report.persona_count:<4d}      ║",
        "╠══════════════════════════════════════════════════════════════╣",
    ]

    for dim in report.dimensions:
        pct = dim.score * 100
        bar_len = int(dim.score * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        lines.append(f"║  {dim.name:<22s} {bar} {pct:>5.1f}%  (w={dim.weight})  ║")
        for k, v in dim.components.items():
            lines.append(f"║    {k:<28s} {v:.3f}                    ║")
        for note in dim.notes:
            lines.append(f"║    ⚠ {note:<52s}  ║")

    lines.append("╠══════════════════════════════════════════════════════════════╣")
    lines.append("║  Per-Persona Scores:                                        ║")
    for pid, score in sorted(report.persona_scores.items()):
        lines.append(f"║    {pid:<20s} {score:>5.1f}                              ║")
    lines.append("╚══════════════════════════════════════════════════════════════╝")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dict-based interface (for raw JSON cohort envelopes without Pydantic)
# ---------------------------------------------------------------------------

def _safe_get(obj: dict, *keys: str, default=None):
    """Nested dict access with default."""
    for k in keys:
        if isinstance(obj, dict):
            obj = obj.get(k, default)
        else:
            return default
        if obj is None:
            return default
    return obj


def compute_pqs_from_dict(cohort: dict) -> dict | None:
    """Compute PQS from a raw JSON cohort envelope dict.

    Returns a plain dict (JSON-serializable) with:
      pqs, behavioral_realism, identity_depth, decision_quality, cohort_health,
      and a components sub-dict.

    Returns None if cohort has no valid personas.
    """
    personas = cohort.get("personas", [])
    personas = [p for p in personas if isinstance(p, dict)]
    summary = cohort.get("cohort_summary", {})
    n = len(personas)
    if n == 0:
        return None

    avg = lambda lst: sum(lst) / len(lst) if lst else 0.0

    # ── Dim 1: Behavioral Realism ──
    bands = {"low": 0, "medium": 0, "high": 0}
    tension_count = 0
    for p in personas:
        di = p.get("derived_insights", {})
        band = di.get("consistency_band", "medium")
        if band in bands:
            bands[band] += 1
        tensions = di.get("key_tensions", [])
        if tensions and len(tensions) >= 1:
            tension_count += 1

    band_counts = [v for v in bands.values() if v > 0]
    if band_counts and n > 0:
        probs = [c / n for c in band_counts]
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        band_diversity = entropy / math.log2(3) if math.log2(3) > 0 else 0
    else:
        band_diversity = 0
    tension_rate = tension_count / n
    dim1 = 0.5 * max(0, band_diversity) + 0.5 * tension_rate

    # ── Dim 2: Identity Depth ──
    narr_scores, ls_scores, mem_scores, rel_scores = [], [], [], []
    for p in personas:
        narr = p.get("narrative", {})
        fp = narr.get("first_person", "") or ""
        tp = narr.get("third_person", "") or ""
        ns = (0.5 if len(fp.split()) >= 80 else len(fp.split()) / 160.0) + \
             (0.5 if len(tp.split()) >= 80 else len(tp.split()) / 160.0)
        narr_scores.append(min(1.0, ns))
        stories = p.get("life_stories", []) or []
        ls_scores.append(min(1.0, len(stories) / 2.5))
        core = _safe_get(p, "memory", "core", default={})
        events = core.get("life_defining_events", []) or []
        mem_scores.append(min(1.0, len(events) / 3.0))
        rel = core.get("relationship_map", {})
        has_partner = bool(rel.get("primary_decision_partner", ""))
        has_inf = len(rel.get("key_influencers", []) or []) >= 1
        rel_scores.append((0.5 if has_partner else 0) + (0.5 if has_inf else 0))
    dim2 = 0.30 * avg(narr_scores) + 0.25 * avg(ls_scores) + 0.25 * avg(mem_scores) + 0.20 * avg(rel_scores)

    # ── Dim 3: Decision Quality ──
    src_scores, obj_scores, bul_scores, con_scores = [], [], [], []
    for p in personas:
        bt = p.get("behavioural_tendencies", {})
        s_count, t_total = 0, 0
        for fname in ("price_sensitivity", "trust_orientation", "switching_propensity"):
            t = bt.get(fname)
            if t and isinstance(t, dict):
                t_total += 1
                if t.get("source", "estimated") in ("grounded", "proxy"):
                    s_count += 1
        src_scores.append(s_count / max(1, t_total))
        obj = bt.get("objection_profile", []) or []
        obj_scores.append(min(1.0, len(obj) / 2.0))
        bullets = p.get("decision_bullets", []) or []
        bul_scores.append(min(1.0, len(bullets) / 4.0))
        core = _safe_get(p, "memory", "core", default={})
        constraints = core.get("immutable_constraints", {}) or {}
        has_b = bool(constraints.get("budget_ceiling"))
        has_nn = len(constraints.get("non_negotiables", []) or []) >= 1
        has_av = len(constraints.get("absolute_avoidances", []) or []) >= 1
        con_scores.append(sum([has_b, has_nn, has_av]) / 3.0)
    dim3 = 0.30 * avg(src_scores) + 0.25 * avg(obj_scores) + 0.20 * avg(bul_scores) + 0.25 * avg(con_scores)

    # ── Dim 4: Cohort Health ──
    dist_score = summary.get("distinctiveness_score", 0.0) or 0.0
    type_dist = summary.get("persona_type_distribution", {})
    unique_types = sum(1 for v in type_dist.values() if v > 0) if isinstance(type_dist, dict) else 0
    type_coverage = min(1.0, unique_types / 8.0)
    ds_div = _normalized_entropy(summary.get("decision_style_distribution", {}))
    ta_div = _normalized_entropy(summary.get("trust_anchor_distribution", {}))
    dim4 = 0.35 * dist_score + 0.25 * type_coverage + 0.20 * ds_div + 0.20 * ta_div

    pqs = (0.25 * dim1 + 0.25 * dim2 + 0.25 * dim3 + 0.25 * dim4) * 100

    return {
        "pqs": round(pqs, 1),
        "behavioral_realism": round(dim1 * 100, 1),
        "identity_depth": round(dim2 * 100, 1),
        "decision_quality": round(dim3 * 100, 1),
        "cohort_health": round(dim4 * 100, 1),
        "persona_count": n,
        "components": {
            "band_diversity": round(max(0, band_diversity), 3),
            "tension_rate": round(tension_rate, 3),
            "narrative_completeness": round(avg(narr_scores), 3),
            "life_story_depth": round(avg(ls_scores), 3),
            "memory_seed_depth": round(avg(mem_scores), 3),
            "relationship_completeness": round(avg(rel_scores), 3),
            "tendency_source_coverage": round(avg(src_scores), 3),
            "objection_profile_depth": round(avg(obj_scores), 3),
            "decision_bullet_count": round(avg(bul_scores), 3),
            "constraint_completeness": round(avg(con_scores), 3),
            "distinctiveness": round(dist_score, 3),
            "type_coverage": round(type_coverage, 3),
            "decision_style_diversity": round(ds_div, 3),
            "trust_anchor_diversity": round(ta_div, 3),
        },
    }


def format_pqs_summary(pqs_dict: dict) -> str:
    """Format a PQS dict as a concise console summary (for internal logging)."""
    pqs = pqs_dict["pqs"]
    d1 = pqs_dict["behavioral_realism"]
    d2 = pqs_dict["identity_depth"]
    d3 = pqs_dict["decision_quality"]
    d4 = pqs_dict["cohort_health"]
    n = pqs_dict["persona_count"]

    bar_len = int(pqs / 5)
    bar = "█" * bar_len + "░" * (20 - bar_len)

    return (
        f"[PQS] {bar} {pqs:.1f}/100  (N={n})\n"
        f"[PQS]   Behavioral Realism: {d1:>5.1f}  |  Identity Depth: {d2:>5.1f}\n"
        f"[PQS]   Decision Quality:   {d3:>5.1f}  |  Cohort Health:  {d4:>5.1f}"
    )
