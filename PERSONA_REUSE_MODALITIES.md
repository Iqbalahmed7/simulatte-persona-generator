# Persona Reuse Modalities
**Simulatte Persona Generator — North Star Document**
**Author:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** Definitive — governs all persona reuse decisions

---

## The Core Idea

A Simulatte persona is a **synthetic person**, not a domain-specific research instrument. The 200 personas generated for LittleJoys are not "LittleJoys personas" — they are real synthetic individuals who happen to have been first instantiated in the context of LittleJoys. The same person who decides whether to buy a pediatric nutrition supplement is the same person who will later decide whether to switch banks, buy a vacation package, or adopt a new app. Their psychology, values, life history, and reasoning patterns travel with them.

This document defines exactly what that means in practice: what travels, what resets, what must be rebuilt, and how the system should manage persona identity over time.

---

## 1. Anatomy of a Persona: What Is and Is Not Domain-Specific

Every `PersonaRecord` has two conceptually distinct layers:

### Layer A — Permanent Identity (fully portable, domain-agnostic)

These fields are identical regardless of what domain the persona was first generated in:

| Field | What it contains | Portable? |
|---|---|---|
| `demographic_anchor` | Age, gender, city, household, income bracket, employment, education | ✅ Fully |
| `life_stories` | 2–3 identity-forming vignettes (marriage, career pivot, health event) | ✅ Fully |
| `derived_insights` | Decision style, trust anchor, risk appetite, primary value orientation, consistency score | ✅ Fully |
| `narrative` | First-person and third-person identity expression | ✅ Fully |
| `memory.core` | Identity statement, key values, life-defining events, relationship map, immutable constraints | ✅ Fully |
| `persona_id` | Globally unique, permanent (Settled Decision S20 — never reused or changed) | ✅ Fully |

These fields represent **who the person is**. They do not change when the domain changes.

### Layer B — Domain Expression (domain-influenced, may require re-grounding)

These fields encode how the person's identity *expresses itself* in a specific market context:

| Field | What it contains | Domain-bound? |
|---|---|---|
| `domain` | The domain label (e.g., `"child-nutrition"`) | ✅ Yes |
| `attributes.domain_specific` | Layer 2 taxonomy attributes extracted from domain data | ✅ Yes — specific to the domain |
| `behavioural_tendencies` | price_sensitivity, trust_orientation, switching_propensity, objection_profile | ⚠️ Partially — bands are domain-informed; psychological root is in Layer A |
| `behavioural_tendencies.*.source` | `"grounded"` / `"proxy"` / `"estimated"` — indicates how well-anchored the tendency is | ✅ Yes — grounding is domain-specific |
| `reasoning_prompt` | Soft prior injected into LLM context for decisions | ✅ Yes — assembled from domain-influenced tendencies |

**The key insight:** The bands on `price_sensitivity` or `trust_orientation` are the person's psychology applied to a specific market. A persona who is "high price sensitivity" in the pediatric nutrition market may be "medium price sensitivity" in a premium fintech product — not because they changed, but because the price reference frame shifted. Layer B is a projection of Layer A onto a domain, not a replacement of it.

---

## 2. What Gets Reset Between Experiments, What Persists

The memory architecture enforces a clean separation governed by Settled Decision S18 (Experiment Isolation):

### What resets at the start of every new experiment

The `WorkingMemoryManager.reset()` method clears these fields entirely:

- `memory.working.observations` — all perceived stimuli from prior experiments
- `memory.working.reflections` — all synthesised patterns from prior experiments
- `memory.working.plans` — active intentions
- `memory.working.brand_memories` — brand-specific experiences
- `memory.working.simulation_state` — turn counter, accumulator, consideration set, last decision

**This is already implemented and automatic.** Every time a persona enters a new experiment, they start with a clean working memory slate. What happened in Experiment A does not bleed into Experiment B at the observation level.

### What persists across all experiments (core memory)

- `memory.core.identity_statement` — permanent
- `memory.core.life_defining_events` — permanent
- `memory.core.key_values` — persists; may be updated only via promotion
- `memory.core.immutable_constraints` — persists
- `memory.core.relationship_map` — persists; may be updated only via promotion
- `memory.core.tendency_summary` — persists

### The promotion mechanism — how experience deepens a persona over time

During any experiment, if a reflection accumulates enough evidence (importance ≥ 9, ≥ 3 source citations, no contradiction with existing core), it is eligible for **promotion from working to core memory**. This is how a persona becomes richer over time.

**Example:** If Priya has been through 5 LittleJoys experiments and consistently reflected that "doctor trust is central to my decisions," that reflection may have been promoted to her `key_values` or `relationship_map.trust_network`. When she is reused in a healthcare domain experiment, this enriched core memory makes her immediately more realistic — she has lived experience rather than a blank slate.

**Implication for reuse:** A persona who has been through more experiments is a *better* persona — not a contaminated one. Core memory accumulation is valuable. Working memory reset is protection against context bleed.

---

## 3. Reusability by Scenario

### Scenario A — Same domain, new experiment (always reusable)

**Example:** LittleJoys persona pool reused for a second LittleJoys study (e.g., testing a new product line).

- Layer A: use as-is ✅
- Layer B: use as-is ✅ (domain_specific attributes and tendency grounding remain valid)
- Working memory: reset ✅ (automatic)
- Core memory: carries forward ✅ (enriched)

**Cost saved:** 100% — zero regeneration required.

---

### Scenario B — Adjacent domain, same taxonomy class (reusable with domain layer swap)

**Example:** LittleJoys personas (pediatric nutrition / CPG) reused for Lo! Foods (health food / CPG).

Both domains are CPG. The base psychology (Layer A) and the broad decision patterns (price sensitivity, brand trust, social proof) are highly transferable. The specific domain attributes differ (pediatrician influence vs. fitness influencer trust), but the person's underlying tendencies are anchored in the same CPG buying psychology.

- Layer A: use as-is ✅
- Layer B — `attributes.domain_specific`: **re-run domain extraction** for Lo! Foods domain data; swap out LittleJoys-specific domain attributes
- Layer B — `behavioural_tendencies`: bands largely carry over (high price sensitivity is high price sensitivity); re-grade source from `"grounded"` to `"estimated"` until Lo! Foods grounding runs
- Working memory: reset ✅
- Core memory: carries forward ✅

**Cost saved:** ~60–70% — identity layer (the expensive LLM generation work) is fully reused. Only domain attribute extraction and tendency re-grounding run fresh.

**How to do it:** Call `domain_extractor.extract_domain_attributes()` on Lo! Foods corpus, then `domain_merger.merge_taxonomy()` to attach the new domain layer. Update `persona.domain = "health-food"`. Regrade tendency sources.

---

### Scenario C — Different domain class (reusable at identity layer only)

**Example:** LittleJoys personas (CPG) reused for a fintech client.

The person's psychology, demographics, life history, and reasoning style are fully portable. But a CPG persona's domain attributes (pediatrician influence, supplement belief, formula trust) have no meaning in fintech. The `attributes.domain_specific` and the domain-grounded tendency expressions must be rebuilt from scratch for the new domain.

- Layer A: use as-is ✅ (this is valuable — you have a fully-formed synthetic person)
- Layer B — `attributes.domain_specific`: rebuild entirely for fintech domain ⚙️
- Layer B — `behavioural_tendencies`: bands carry over as priors (source = `"estimated"`); re-ground against fintech data for full validity ⚙️
- `domain` field: update to new domain string
- Working memory: reset ✅
- Core memory: carries forward ✅

**Cost saved:** ~40–50% — identity generation (demographics, life stories, derived insights, core memory) is fully reused. Domain layer is rebuilt, but this is cheaper than full persona generation.

**Important:** Until re-grounding completes, tendencies have source `"estimated"` — the persona is operating in Proxy Mode for the new domain. This is transparent and valid, but not as accurate as grounded tendencies.

---

### Scenario D — Completely new ICP, different demographics

**Example:** Using LittleJoys Indian urban mothers (25–40) for a study targeting urban Indian men (30–50) in a fintech context.

- Layer A: **demographic match fails** — the personas' demographics are wrong for the target ICP. Reuse is not appropriate.
- Correct action: generate new personas for the new demographic profile; optionally reuse a subset of personas that happen to fall within the new ICP (see §4 on matching).

**Cost saved:** Variable — only demographically compatible individuals from the pool can be reused.

---

## 4. Persona Registry — The Correct Architecture

### The problem with the current state

Currently, personas are stored inside client project repositories (e.g., `simulatte_cohort_final.json` in the LittleJoys data folder). The Persona Generator has no memory of what it has previously created. Every new cohort request generates fresh personas from scratch — even when demographically identical personas already exist.

This is architecturally wrong. It means:
- Wasteful regeneration — paying LLM costs to recreate synthetic people who already exist
- No accumulated depth — each persona starts fresh with zero core memory
- No cross-client learning — insights from Lo! Foods experiments cannot enrich personas being used in a LittleJoys study

### The correct architecture: Persona Generator as the system of record

The Persona Generator should maintain a **central persona registry** — a persistent store of all ever-generated `PersonaRecord` objects, indexed for retrieval.

```
Persona Generator (system of record)
  /data/registry/
    personas/
      pg-lj-001.json      ← Full PersonaRecord, latest version
      pg-lj-002.json
      pg-lf-001.json      ← Lo! Foods personas
      ...
    index/
      demographics.json   ← Index: age_band + city_tier + gender → [persona_ids]
      domain_history.json ← Index: persona_id → [domain, date] history
      core_versions.json  ← Index: persona_id → version history of core memory
```

Client projects (LittleJoys app, Lo! Foods) **never own personas**. They hold references — a list of `persona_id` strings — and call back to the Persona Generator's registry to retrieve the current `PersonaRecord` for each ID.

### Registry lookup before generation

Before generating any new persona, the generator checks the registry:

```
1. Extract demographic requirements from ICP spec (age band, city tier, gender, household)
2. Query registry: find personas whose demographic_anchor matches ICP requirements
3. Filter: check domain compatibility (same class = reuse directly; different class = reuse Layer A)
4. If sufficient matches found: reuse matched personas (update domain layer if needed)
5. If insufficient matches: generate new personas for the gap only
6. Add all new personas to registry
```

**Result:** Over time, the registry grows into a deep pool of well-travelled synthetic people. New client studies draw from existing personas wherever possible and only generate genuinely new ones when the demographic or psychological profile doesn't yet exist.

---

## 5. Where Personas Are Stored and How Projects Access Them

### Storage: Persona Generator is authoritative

All `PersonaRecord` objects live in the Persona Generator's central registry. This is the only place where the definitive, up-to-date version of each persona lives.

**Location:** `/data/registry/personas/` in the Persona Generator repository.

**Format:** One JSON file per persona, named `{persona_id}.json`. Full `PersonaRecord` serialisation.

### Client projects: reference, don't own

Client projects (LittleJoys, Lo! Foods, future clients) store:
1. A **cohort manifest** — a JSON file listing the `persona_id` values assigned to that client's cohort, plus the domain and experiment context
2. A **snapshot** — optionally, a point-in-time copy of the cohort for reproducibility (tagged with date and spec hash)

```json
// LittleJoys cohort manifest (what the project stores)
{
  "cohort_id": "lj-cohort-v3",
  "domain": "child-nutrition",
  "icp_spec_hash": "abc123",
  "persona_ids": ["pg-lj-001", "pg-lj-002", ..., "pg-lj-200"],
  "snapshot_date": "2026-04-03",
  "registry_version": "simulatte-v1.2"
}
```

### How the Persona Generator is accessed

The Persona Generator exposes a **registry API** (initially CLI, later API endpoint):

```bash
# Retrieve a persona by ID (always returns current version from registry)
simulatte registry get --id pg-lj-001

# Find personas matching demographic criteria
simulatte registry find --age-min 28 --age-max 40 --city-tier metro --gender female

# Export a cohort snapshot for a client project
simulatte registry export --cohort-id lj-cohort-v3 --output /path/to/client/data/

# Register a persona from an external project back into the registry (after experiments enrich core memory)
simulatte registry sync --cohort-path /path/to/cohort_final.json
```

The `app_adapter.py` (already built in Sprint 23) is the bridge: it calls `load_simulatte_cohort()` which reads from the central registry path, not from the client project's local copy.

---

## 6. Requirements to Reuse a Persona

A persona may be reused when ALL of these conditions are met:

### Mandatory conditions

| Condition | Check | What to do if fails |
|---|---|---|
| **Demographic match** | Persona's `demographic_anchor` (age, tier, gender, household) falls within new ICP's target segment | Do not reuse; generate new persona |
| **Mode compatibility** | If new experiment requires `grounded` mode, persona must have been grounded or be re-groundable | Re-run domain extraction; update `behavioural_tendencies.source` |
| **Working memory reset** | `memory.working` has been reset via `WorkingMemoryManager.reset()` before the new experiment | Mandatory; automatic if using `run_loop` correctly |
| **Domain layer updated** | If new domain differs from persona's `persona.domain`, Layer B has been updated or marked `"estimated"` | Re-run domain extension or downgrade to Proxy Mode transparently |

### Optional but recommended

| Condition | Benefit |
|---|---|
| **Prior experiments run** | Persona has accumulated promoted core memory — richer reasoning |
| **Same broad cultural/geographic context** | An urban North Indian persona is more valid in a Mumbai fintech study than a rural South India study, even if demographics technically match |
| **Consistency score ≥ 70** | Personas with high consistency scores produce more reliable simulation output |

---

## 7. What Happens to Core Memory on Reuse — Does It Help or Hurt?

This is the most important nuance in persona reuse.

### Core memory accumulation is a feature, not a bug

When Priya has been used in 5 LittleJoys experiments over 6 months, her core memory may have been enriched through promotion events:
- Her `key_values` now explicitly includes "doctor-validated choices only"
- Her `relationship_map.key_influencers` now includes "pediatric nutritionist"
- Her `immutable_constraints.non_negotiables` includes "no products with artificial preservatives"

When Priya is reused in a Lo! Foods health food study, this accumulated core memory makes her **more realistic**, not less. She's a more complete person. Her strong healthcare authority bias and ingredient scrutiny are valid psychological traits that belong in a health food context too.

### When does accumulated core memory become problematic?

Only if the new experiment's domain is so disconnected from prior experiments that the promoted memories create implausible context. Example: Priya's core memory now strongly references "pediatric nutrition contexts" in her `tendency_summary` — if reused in a motorcycle accessories study, this creates cognitive dissonance.

**The guard:** Check whether promoted core memories are domain-specific or domain-agnostic before reuse:
- "I prioritise verified health claims" → domain-agnostic → travels with her anywhere
- "I always check with my pediatrician before buying supplements for my child" → CPG/health-specific → valid in adjacent domains, odd in unrelated ones

**Rule of thumb:** If promoted core memory references domain-specific objects (supplement, pediatrician, infant formula), flag for review before reusing in a completely different domain class. If it references values, relationships, or psychological patterns, it travels cleanly.

### Working memory never contaminates reuse

Because working memory is fully reset at the start of every experiment (Settled Decision S18), there is zero contamination from prior experiment observations. Priya's memory of evaluating Product X in Experiment 3 is completely gone when she enters Experiment 6. Only what was promoted to core memory persists — and promotions only happen when something was important enough and consistent enough to be considered a genuine part of her identity.

---

## 8. Persona Versioning

As a persona's core memory evolves through experiments, the registry must maintain version history:

```
pg-lj-001
  v1.0 — 2026-01-15 — Initial generation (LittleJoys cohort v1)
  v1.1 — 2026-02-20 — Core memory promotion: key_values updated after Journey A experiment
  v1.2 — 2026-04-03 — Domain layer extended for Lo! Foods; behavioural_tendencies re-grounded
  v2.0 — 2026-06-10 — Core memory promotion: relationship_map updated after Lo! Foods study
```

**Rule:** A new version is cut whenever:
- A core memory promotion occurs
- The domain layer is re-extended for a new domain
- A major spec upgrade requires recomputation of derived_insights

**Snapshot references:** Client project cohort manifests reference a specific version (`pg-lj-001@v1.1`) for reproducibility. Simulations can be re-run against the same persona version.

---

## 9. Cost and Resource Implications

### Full generation cost breakdown (current state, no registry)

For 200 new personas in Grounded Mode:
- Demographic + life story generation (Sonnet): ~200 LLM calls
- Attribute filling (Sonnet): ~200 LLM calls
- Domain extraction from corpus (Sonnet): 1 batch call
- Narrative generation (Sonnet + optional Sarvam): ~200 LLM calls
- Total: ~600+ Sonnet calls per fresh cohort

### Reuse cost breakdown (with registry)

**Same domain reuse:** 0 LLM calls. Registry lookup only.

**Adjacent domain reuse (Layer B swap):**
- Domain extraction from new corpus: 1 batch Haiku call
- Tendency re-grounding: deterministic computation
- Total: ~1–5 LLM calls for the entire cohort

**Different domain class (Layer A reuse, Layer B rebuild):**
- Domain extraction: 1 batch Haiku call
- Layer B attribute filling: ~200 Haiku calls (cheaper tier)
- Total: ~200 Haiku calls (vs ~600 Sonnet calls from scratch)
- **Cost saving: ~70–80%**

### Registry ROI over time

| After N client studies | % of new personas requiring full generation |
|---|---|
| 1 study (200 personas) | 100% |
| 3 studies (same ICP) | ~10% — mostly gap-fills |
| 5 studies (adjacent domains) | ~5% — rare demographic gaps only |
| 10+ studies (mixed domains) | <5% — registry covers almost all ICP profiles |

---

## 10. Aspects Not to Miss

### Persona consent and attribution
The registry creates a long-lived synthetic identity. The `persona_id` is permanent (S20). Any data derived from a persona should reference its ID — calibration records, simulation traces, tendency shift logs — so the persona's full history is auditable. This is the P10 (traceability) principle applied to persona lifetime.

### ICP drift over time
A persona generated in 2026 for a 28-year-old urban mother will be demographically mismatched if reused in 2030 (she is now 32). The registry should flag personas whose `demographic_anchor.age` has drifted outside the current ICP's age band. The **persona aging system** (Sprint 19) already handles this: `aging_status` tracks whether a persona has been aged and by how much.

### Registry as ground truth vs. calibration
Calibration state (`calibration_state`) is a **cohort-level** concept, not a persona-level one. A persona does not have a calibration state — a cohort does. When personas are reused in a new cohort, the new cohort starts `uncalibrated` and must be independently calibrated against the new domain's benchmarks. Do not carry cohort-level calibration across domains.

### Privacy and synthetic data governance
Registry personas are synthetic but may reflect real demographic distributions. The registry must be treated as sensitive data — not published externally, not used to infer real individuals, access-controlled within the engineering team.

### The "blank slate" trap
Do not reset core memory to make reuse feel "cleaner." A persona with accumulated core memory is more valuable, not less. The temptation to periodically purge core memory to "start fresh" should be resisted — it destroys the depth that makes the persona useful across experiments.

---

## 11. Summary — Decision Rules for Persona Reuse

```
REUSE DECISION TREE
====================

New experiment received. ICP spec defined.

Step 1: Query registry for demographic matches
  → If < 80% coverage: generate new personas for the gap; add to registry
  → If ≥ 80% coverage: proceed with registry personas

Step 2: Check domain compatibility
  → Same domain as prior use: reuse Layer A + Layer B as-is
  → Adjacent domain (same taxonomy class): reuse Layer A; swap Layer B (re-extract)
  → Different domain class: reuse Layer A; rebuild Layer B from scratch
  → Demographic mismatch: do not reuse; generate new

Step 3: Memory handling
  → Always reset working memory before new experiment (automatic in run_loop)
  → Never reset core memory (it carries forward — this is valuable)
  → Flag core memory entries that are domain-specific before cross-domain reuse

Step 4: Post-experiment
  → Sync enriched personas (promoted core memories) back to registry
  → Cut new version if core memory was promoted or domain layer was updated
  → Update cohort manifest in client project with registry version reference
```

---

## Implementation Roadmap

The following are not yet built and represent the next engineering requirement to realise full persona reuse:

| Feature | Priority | What it requires |
|---|---|---|
| Central persona registry (file store + index) | HIGH | New `src/registry/` module; `persona_registry.py` with add/get/find/sync operations |
| Registry lookup before generation | HIGH | Modify `cohort/assembler.py` to check registry before calling generation pipeline |
| Persona versioning | MEDIUM | Add `version` and `version_history` to `PersonaRecord` or registry metadata |
| Domain layer swap utility | MEDIUM | `persona_regrounder.py`: takes PersonaRecord + new domain data → returns updated PersonaRecord with new Layer B |
| Registry CLI commands | MEDIUM | `simulatte registry get/find/export/sync` |
| Cohort manifest format | LOW | Standardise client project manifest (persona_ids + registry_version reference) |
| ICP drift detection | LOW | Compare `demographic_anchor.age` against current date + ICP age band; flag aged-out personas |
