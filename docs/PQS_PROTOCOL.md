# Persona Quality Score (PQS) Protocol

**Last updated:** 2026-05-09
**Module:** `src/quality/pqs.py`

PQS is Simulatte's primary quality signal for generated personas. Every
persona that enters a study, a simulation, or a client-facing output must
carry a PQS score. Personas that fall below the acceptance threshold are
regenerated or quarantined — they never reach downstream features.

---

## What PQS measures

PQS is a 0–100 composite built from four equally weighted dimensions (25%
each). Each dimension targets a different failure mode.

### Dimension 1 — Behavioral Realism (25%)
**Failure mode it catches:** all personas converging to the same
"high-consistency rational consumer" archetype.

| Component | Weight | What it checks |
|-----------|--------|----------------|
| `consistency_band_diversity` | 50% | Shannon entropy of low/medium/high consistency bands across cohort. Low score = everyone is "high consistency" = boring. |
| `tension_presence` | 50% | Fraction of personas with ≥ 1 key tension. Tension is the engine of realistic decision-making. |

Target range: **65–85**. Above 85 suggests artificial diversity; below 50
means the cohort is psychologically flat.

---

### Dimension 2 — Identity Depth (25%)
**Failure mode it catches:** personas that are demographic shells with no
biographical substance — they look plausible in a table but break down in
conversation.

| Component | Weight | What it checks |
|-----------|--------|----------------|
| `narrative_completeness` | 30% | first_person ≥ 80 words AND third_person ≥ 80 words |
| `life_story_depth` | 25% | Avg life stories per persona (target: 2–3) |
| `memory_seed_depth` | 25% | Avg `life_defining_events` in core memory (target: 3) |
| `relationship_completeness` | 20% | Has `primary_decision_partner` + ≥ 1 `key_influencer` |

Target range: **60–90**. Swift-tier personas score 0–30 on this dimension
because they have no life stories or memory — this is the primary reason
Swift is not acceptable for research output.

---

### Dimension 3 — Decision Quality (25%)
**Failure mode it catches:** personas with behavioural tendencies that were
estimated generically rather than grounded in actual domain signals.

| Component | Weight | What it checks |
|-----------|--------|----------------|
| `tendency_source_coverage` | 30% | Fraction of tendencies with source = "grounded" or "proxy" (not "estimated") |
| `objection_profile_depth` | 25% | Avg objection count per persona (target: ≥ 2) |
| `decision_bullet_count` | 20% | Avg decision bullets (target: 4) |
| `constraint_completeness` | 25% | Has budget_ceiling + non_negotiables + absolute_avoidances |

Target range: **55–80**. Domains with rich corpus data score higher because
tendencies are grounded; generic runs without domain_data score lower here.

---

### Dimension 4 — Cohort Health (25%)
**Failure mode it catches:** a set of individually reasonable personas that
are all too similar to each other — cohort-level clustering.

| Component | Weight | What it checks |
|-----------|--------|----------------|
| `distinctiveness` | 35% | Distinctiveness score from `cohort_summary` (0–1) |
| `type_coverage` | 25% | Unique persona types out of 8 possible |
| `decision_style_diversity` | 20% | Shannon entropy of decision style distribution |
| `trust_anchor_diversity` | 20% | Shannon entropy of trust anchor distribution |

Target range: **50–80**. Small cohorts (n < 5) score lower on entropy
dimensions — this is expected and not a quality failure.

---

## Acceptance thresholds

These are the minimum scores required for a persona or cohort to proceed.
Anything below is regenerated; persistent failures abort the run.

| Tier | Per-persona minimum | Cohort minimum | Notes |
|------|---------------------|----------------|-------|
| Swift | Not enforced | Not enforced | Swift is preview-only; no study outputs |
| **Core** | **60 / 100** | **65 / 100** | Default for all production use |
| Complete | 65 / 100 | 70 / 100 | Simulation-ready requires higher Identity Depth |

**Rationale for 60/65:**
- A per-persona score of 60 requires passing on at least 3 of the 4 individual
  sub-components (narrative, life stories, memory, tensions, bullets).
- A cohort score of 65 requires all four dimensions to clear roughly 65% of
  their maximum — unachievable if the cohort is clustered or narratives are
  empty.
- These are conservative floors. Scores below 75 cohort-level should trigger
  a warning even if they don't abort.

### Warning band
| Cohort PQS | Status |
|------------|--------|
| < 65 | ❌ Abort — cohort fails minimum threshold |
| 65–74 | ⚠️ Warning — usable but flag to operator |
| 75–84 | ✅ Acceptable |
| 85–100 | ✅ Excellent |

---

## How PQS is integrated in the pipeline

### Current state (as of 2026-05-09)
PQS is computed in `src/orchestrator/invoke.py` step 7b, immediately after
cohort assembly. It is logged to console and stored in `cohort_envelope["_pqs"]`
for historical tracking. **It does not yet gate persona delivery.**

### Target state — PQS as a hard gate

The gate should fire in two places:

**Gate A — Per-persona gate (inside `_run_generation`)**
After `assemble_cohort()` returns the envelope, score each persona individually.
Personas below the per-persona threshold are collected and passed to
`_regenerate_failing()`. This already exists as a pattern for G12 failures —
PQS just adds another rejection criterion.

**Gate B — Cohort gate (in `invoke.py` step 7b)**
After per-persona regeneration, compute cohort-level PQS. If below cohort
threshold, raise a `RuntimeError` with the dimension breakdown so the operator
knows which dimension failed and why.

### Implementation sketch

```python
# In invoke.py step 7b — replace the current try/except block:

PQS_COHORT_FLOOR = float(os.getenv("PQS_COHORT_FLOOR", "65"))
PQS_PERSONA_FLOOR = float(os.getenv("PQS_PERSONA_FLOOR", "60"))

pqs_score: float | None = None
try:
    from src.quality.pqs import compute_pqs_from_dict, format_pqs_summary
    pqs_report = compute_pqs_from_dict(cohort_envelope)
    if pqs_report is not None:
        pqs_score = pqs_report["pqs"]
        print(format_pqs_summary(pqs_report))
        cohort_envelope["_pqs"] = pqs_report

        # Gate B — cohort floor
        if pqs_score < PQS_COHORT_FLOOR:
            low_dims = {
                k: v for k, v in {
                    "Behavioral Realism": pqs_report["behavioral_realism"],
                    "Identity Depth":     pqs_report["identity_depth"],
                    "Decision Quality":   pqs_report["decision_quality"],
                    "Cohort Health":      pqs_report["cohort_health"],
                }.items() if v < PQS_COHORT_FLOOR
            }
            raise RuntimeError(
                f"PQS cohort gate failed: {pqs_score:.1f} < {PQS_COHORT_FLOOR} floor. "
                f"Failing dimensions: {low_dims}. "
                f"Check domain data quality or increase cohort size."
            )
        elif pqs_score < 75:
            import warnings
            warnings.warn(
                f"[PQS] Cohort score {pqs_score:.1f} is below 75 — usable but borderline.",
                stacklevel=2,
            )
except RuntimeError:
    raise  # re-raise gate failures
except Exception as e:
    logging.getLogger(__name__).debug("PQS computation skipped: %s", e)
```

Per-persona gate A should be wired into `_regenerate_failing()` in `cli.py`
by computing a quick per-persona score before calling G12.

### Per-persona PQS via `compute_pqs_from_dict`

The dict-based function returns `pqs_report["components"]` which is cohort-level.
Per-persona scoring uses the simplified formula in `compute_pqs()` (Pydantic path):

```
p_score = 0.25 × narrative + 0.20 × life_stories + 0.20 × memory
        + 0.15 × tensions + 0.20 × decision_bullets
```

This is intentionally lighter than the cohort formula — cohort health
dimensions (distinctiveness, type coverage) can only be computed once the full
cohort is assembled.

---

## Env vars

| Variable | Default | Description |
|----------|---------|-------------|
| `PQS_COHORT_FLOOR` | `65` | Cohort-level PQS gate. Cohorts below this abort the run. |
| `PQS_PERSONA_FLOOR` | `60` | Per-persona PQS gate. Personas below trigger regeneration. |
| `PQS_WARN_THRESHOLD` | `75` | Cohort scores below this emit a warning but don't abort. |

Set these in Railway environment variables or `.env`. Lower the floor
temporarily (e.g. `PQS_COHORT_FLOOR=50`) for dev/debug runs without
affecting production.

---

## Reading PQS from a stored cohort

Every cohort JSON produced by the pipeline stores its PQS report under the
`_pqs` key:

```json
{
  "cohort_id": "abc123",
  "personas": [...],
  "cohort_summary": {...},
  "_pqs": {
    "pqs": 71.4,
    "behavioral_realism": 68.0,
    "identity_depth": 79.2,
    "decision_quality": 58.3,
    "cohort_health": 74.1,
    "persona_count": 10,
    "components": { ... }
  }
}
```

To recompute PQS on a stored cohort (e.g. to check historical runs):

```bash
python3 -c "
import json
from src.quality.pqs import compute_pqs_from_dict, format_pqs_summary
cohort = json.load(open('outputs/cohort_abc123.json'))
print(format_pqs_summary(compute_pqs_from_dict(cohort)))
"
```

---

## PQS in The Mind benchmark

The benchmark service (`services/benchmark/`) runs 10 independent quality
tests against a persona. These tests measure different things than PQS:

| | PQS | Benchmark |
|--|-----|-----------|
| **What** | Structural completeness of the persona data | Behavioural fidelity in conversation |
| **When** | At generation time, before delivery | Post-hoc, run manually by operator |
| **Gate** | Hard — blocks delivery | Soft — grades the persona, no blocking |
| **Score** | 0–100 composite | A+/A/B/C/D grade |
| **Focus** | Fields, depth, diversity | Role-play authenticity, contradiction handling |

PQS and benchmark grades are complementary. A persona can have high PQS
(all fields populated) but a low benchmark grade (the LLM plays the role
inconsistently). Investigating the gap between them reveals which layer of
the pipeline to improve.

---

## Common failure patterns and fixes

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Identity Depth < 50 | No life stories generated | Check `life_story_generator.py`; increase `_DEFAULT_N_STORIES` |
| Decision Quality < 50 | No domain_data provided | Pass `domain_data` or `corpus_path` to grounding |
| Behavioral Realism < 50 | All personas in same consistency band | Investigate `demographic_sampler.py` band assignment |
| Cohort Health < 40 | Personas are clustering | Increase pool size; check stratification thresholds |
| All dimensions moderate (55–65) | Generic run, no corpus | Expected without domain data; add corpus or increase n |
