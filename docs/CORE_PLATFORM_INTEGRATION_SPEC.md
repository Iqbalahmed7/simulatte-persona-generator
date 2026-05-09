# Simulatte Core Platform — Integration Specification

**Version:** 1.0  
**Date:** 2026-05-09  
**Status:** Ground truth — build against this

This document specifies how the new Simulatte Core Platform integrates with
the Persona Generator. It covers the exact API contracts, shared data models,
service boundaries, env vars, error handling, and sequencing for IRIS and
Forge as hosted products on the platform.

---

## 1. Platform overview

The Core Platform is a single deployable service that hosts both IRIS and
Forge. It replaces the current arrangement where Forge calls IRIS's pool
service, and IRIS calls Persona Generator separately.

```
┌──────────────────────────────────────────────────────────────────┐
│                     SIMULATTE CORE PLATFORM                      │
│                                                                  │
│   ┌─────────────────────────┐   ┌─────────────────────────────┐ │
│   │          IRIS           │   │           FORGE             │ │
│   │  Creative pre-testing   │   │   Concept testing / panels  │ │
│   └────────────┬────────────┘   └──────────────┬──────────────┘ │
│                │                               │                 │
│                └──────────────┬────────────────┘                 │
│                               │                                  │
│              ┌────────────────▼──────────────────┐               │
│              │        PERSONA POOL SERVICE        │               │
│              │  Owns all persona lifecycle:       │               │
│              │  generation → PQS gate → registry  │               │
│              │  → sampling → identity assignment  │               │
│              └────────────────┬──────────────────┘               │
└───────────────────────────────┼──────────────────────────────────┘
                                │ HTTP
                                ▼
              ┌─────────────────────────────────────┐
              │        SIMULATTE ENGINE              │
              │  simulatte-engine / Railway          │
              │  POST /generate                      │
              │  POST /persona/deep-study (async)    │
              │  GET  /job/{job_id}                  │
              └─────────────────────────────────────┘
                                │
                                │ Python (in-process)
                                ▼
              ┌─────────────────────────────────────┐
              │      PERSONA GENERATOR               │
              │  src/orchestrator/invoke.py          │
              │  Core pipeline (mode=deep)           │
              │  PQS Gate A + B                      │
              │  Registry read/write                 │
              └─────────────────────────────────────┘
```

### Tier used by platform
**Core tier (mode="deep")** is the default for all platform-generated personas.
Complete tier (mode="simulation-ready") is only triggered when Forge or IRIS
requests an agent-simulation run. Swift (2-call Haiku) is never used for
production outputs — only for instant UI previews before a pool is generated.

---

## 2. Persona Pool Service

The Persona Pool Service is the single integration boundary between the
platform and Persona Generator. Neither IRIS nor Forge calls PG directly —
they both call the pool service.

### 2.1 Pool lifecycle

```
CREATE POOL (ICP + size + segment)
       │
       ▼
  [pool.status = "generating"]
       │
       ├── Call Engine POST /generate
       │     - n_personas = requested size × 1.2 (buffer for PQS failures)
       │     - Wait synchronously (Engine timeout: 20 min)
       │
       ├── Receive persona dossiers
       │
       ├── PQS already gated by PG (Gate A + B)
       │
       ├── Assign wr_persona_id (ULID) per dossier
       │
       ├── Persist to pool store (platform DB)
       │
       └── [pool.status = "ready"]  →  notify caller via webhook or polling
```

### 2.2 Pool create request

`POST /internal/pools/generate`  
Called by IRIS or Forge when a new audience pool is needed.

```json
{
  "pool_id":       "pool_01JXXXXXXXX",
  "caller":        "iris" | "forge",
  "segment":       "urban_mothers_india",
  "market":        "IN",
  "age_min":       25,
  "age_max":       40,
  "gender":        "female" | "male" | null,
  "n_personas":    10,
  "domain":        "cpg",
  "business_problem": "Post-trial lapse: why mothers stop after first month",
  "pipeline_mode": "core" | "complete",
  "webhook_url":   "https://platform.simulatte.io/webhooks/pool-ready"
}
```

**Fields:**
- `n_personas` — personas requested. Pool service requests `n_personas + 2`
  from Engine to buffer against PQS gate quarantines.
- `pipeline_mode` — `core` maps to `mode="deep"`, `complete` maps to
  `mode="simulation-ready"`. Default: `core`.
- `webhook_url` — optional. If present, POST'd when pool reaches `ready` or
  `failed`. If absent, caller must poll `GET /internal/pools/{pool_id}`.

### 2.3 Pool sample request

`GET /internal/pools/{pool_id}/sample?n=5&seed=abc`  
Returns n personas from an existing ready pool.

```json
{
  "pool_id": "pool_01JXXXXXXXX",
  "personas": [
    {
      "wr_persona_id": "wrp_01JYYYYYYY",
      "persona_id":    "pg-001",
      "age":           32,
      "gender":        "female",
      "city_tier":     1,
      "market":        "IN",
      "segment":       "urban_mothers_india",
      "pqs_score":     72.4,
      "dossier": { ... full persona JSON ... }
    }
  ],
  "count":    5,
  "pool_pqs": 71.8
}
```

**Identity rules:**
- `wr_persona_id` — the platform-canonical identity. Assigned at pool creation.
  Used for memory alignment across IRIS and Forge. Never reassigned.
- `persona_id` — the PG-internal identifier (e.g. `pg-001`). Preserved for
  traceability but NOT used as the cross-module identity key.
- Both identifiers travel with every persona in every downstream call.

### 2.4 Pool status

`GET /internal/pools/{pool_id}`

```json
{
  "pool_id":      "pool_01JXXXXXXXX",
  "status":       "generating" | "ready" | "failed" | "partial",
  "n_requested":  10,
  "n_delivered":  9,
  "pqs_score":    71.8,
  "pqs_passed":   true,
  "created_at":   "2026-05-09T10:00:00Z",
  "ready_at":     "2026-05-09T10:04:12Z",
  "error":        null
}
```

`partial` status: Engine delivered fewer than `n_requested` due to PQS
quarantines. Pool is usable if `n_delivered >= n_requested × 0.80`.

---

## 3. Persona Generator API contract

The platform calls Engine via HTTP. This section is the exact contract — do
not deviate.

### 3.1 Synchronous generation — `POST /generate`

**URL:** `{ENGINE_URL}/generate`  
**Auth:** `Authorization: Bearer {ENGINE_SECRET}`  
**Timeout:** 20 minutes (1200s)  
**Use for:** all pool generation calls from platform

```json
// Request
{
  "n_personas":        10,
  "market":            "IN",
  "domain":            "cpg",
  "business_problem":  "Post-trial lapse: why mothers stop after first month",
  "age_min":           25,
  "age_max":           40
}
```

```json
// Response 200
{
  "cohort_id":       "cohort-abc123",
  "personas":        [ { ...full dossier... } ],
  "count_delivered": 9
}
```

**Error responses:**
- `500` — generation failed. Body: `{ "detail": "Persona generation failed: <type>: <msg>" }`
  - PQS gate failure looks like: `"PQS cohort gate failed: 58.3 / 100 (floor=65). ..."`
  - Pool service must surface this error to the caller — never silently retry
    with a lower quality threshold.

**Env var that affects this call:**
```
ENGINE_URL=https://simulatte-engine.railway.app
ENGINE_SECRET=<secret>
PG_REGISTRY_PATH=/mnt/pg_registry   # set on Engine's Railway volume
```

### 3.2 Async generation + simulation — `POST /persona/deep-study`

**Use for:** Forge concept tests that need agent simulation (pipeline_mode="complete")

```json
// Request
{
  "study_name":       "LittleJoys Post-Trial Study",
  "region":           "India",
  "n_personas":       15,
  "domain":           "cpg",
  "research_question": "Why do mothers stop after trial?",
  "scenario_question": "Would you repurchase LittleJoys Family Pack?",
  "scenario_context":  "You bought LittleJoys last month. Your child liked it...",
  "scenario_options":  ["Yes, repurchase", "No, switching brands", "Undecided"],
  "age_min":           25,
  "age_max":           40,
  "icp_description":   "Urban mothers with children under 5"
}
```

Returns immediately with a job:
```json
{ "job_id": "job_abc123", "status": "queued" }
```

Poll with `GET /job/{job_id}`:
```json
{
  "job_id":   "job_abc123",
  "status":   "running" | "done" | "failed",
  "result": {
    "cohort_id":            "cohort-abc",
    "persona_count":        15,
    "health_score":         0.88,
    "initial_distribution": [ {...} ],
    "cost_usd":             0.18
  }
}
```

**Poll cadence:** every 15s, timeout after 25 min.

### 3.3 Persona dossier schema

The `personas` array in `/generate` responses contains full dossier objects.
The platform must store these verbatim — never transform or summarise them.
Key fields used by IRIS and Forge:

```typescript
interface PersonaDossier {
  // Identity
  persona_id:           string;          // PG internal — "pg-001"
  
  // Demographics (for ICP matching + display)
  demographic_anchor: {
    name:        string;
    age:         number;
    gender:      string;
    location:    { city: string; country: string; city_tier?: number };
    employment:  { occupation: string; industry: string; seniority: string };
    education:   string;
    life_stage:  string;
    household:   { size: number; composition: string };
  };
  
  // Psychology (for IRIS exposure simulation)
  derived_insights: {
    decision_style:             string;
    trust_anchor:               string;
    risk_appetite:              string;
    key_tensions:               string[];
    consistency_score:          number;
    consistency_band:           "low" | "medium" | "high";
    primary_value_orientation:  string;
    coping_mechanism:           { type: string; description: string };
  };
  
  // Behaviour (for Forge scoring)
  behavioural_tendencies: {
    price_sensitivity:    { band: string; description: string };
    switching_propensity: { likelihood: string; triggers: string[] };
    objection_profile:    { type: string; likelihood: string; description: string }[];
    trust_orientation:    Record<string, string>;
    reasoning_prompt:     string;
  };
  
  // Identity depth (for conversation / simulation)
  narrative: {
    first_person:  string;   // ≥ 80 words — persona speaks in first person
    third_person:  string;   // ≥ 80 words — third-person observer view
  };
  life_stories: { title: string; narrative: string; when: string }[];
  decision_bullets: string[];
  
  // Memory (for IRIS memory-chain quotes)
  memory: {
    core: {
      identity_statement:    string;
      key_values:            string[];
      life_defining_events:  string[];
      relationship_map:      { primary_decision_partner: string; key_influencers: string[] };
      immutable_constraints: { budget_ceiling: string; non_negotiables: string[]; absolute_avoidances: string[] };
      tendency_summary:      string;
    };
    working?: {
      observations: any[];
      reflections:  any[];    // populated in "complete" tier only
    };
  };
  
  // Quality
  _pqs?: {
    pqs:                 number;    // 0–100
    behavioral_realism:  number;
    identity_depth:      number;
    decision_quality:    number;
    cohort_health:       number;
  };
}
```

---

## 4. IRIS integration

### 4.1 Persona pool for IRIS

IRIS creates pools on demand when a user configures a test audience. The
pool service is the only entry point.

**IRIS pool creation trigger:**  
User clicks "Build audience" → IRIS calls `POST /internal/pools/generate` with
segment + ICP. Pool status shown as "Generating your audience…" in UI. IRIS
polls or listens for webhook. When `status=ready`, audience is available for
test runs.

**Recommended pool sizes:**
- Quick preview (pre-flight reveal): 5 personas
- Standard test: 10 personas
- Pro / brand test: 20 personas

**Pre-flight reveal:**  
Show personas as characters before the exposure loop. Pull from the dossier:
- `demographic_anchor.name`
- `demographic_anchor.age`, `.gender`, `.location.city`
- `demographic_anchor.employment.occupation`
- `derived_insights.decision_style` — render as archetype label
- `derived_insights.trust_anchor` — render as anchor belief
- `derived_insights.primary_value_orientation`

See Litmus learnings §1: showing the panel as characters before the run is
what converts the verdict from "AI output" to "something the panel said."

### 4.2 Exposure simulation call

IRIS runs each persona through an exposure loop using the persona's system
prompt built from the dossier. This call is made INSIDE the platform using
the existing `services/benchmark/system_prompt.py` builder — no separate API.

```python
from services.benchmark.system_prompt import build_system_prompt

system_prompt = build_system_prompt(persona_dossier)
# → Full system prompt with all 10 sections including
#   SECTION 6 contradiction reframing (no self-disclosure)
```

Build the system prompt once per persona per test run. Pass it to Claude as
the system message. The exposure conversation is IRIS's responsibility —
Persona Generator only builds the persona.

**Critical — memory grounding for IRIS quotes:**  
Each verbatim quote in IRIS output must expose 2–3 retrieved memories from
the persona's `memory.core.life_defining_events`. Inject them into the
exposure prompt under a "What you remember" section (see LEARNINGS_FOR_IRIS_FORGE §2.1):

```
RELEVANT MEMORIES (use these when reasoning about this stimulus):
- [event 1 from life_defining_events]
- [event 2]
- [event 3]
Evaluate ONLY what's in the brief. Do NOT invent product details.
```

### 4.3 IRIS-to-PG identity alignment

Every persona exposed in IRIS carries both `wr_persona_id` (platform-canonical)
and `persona_id` (PG-internal). When a Forge test draws from the same pool,
the `wr_persona_id` is the key that links memory events between products. The
platform DB must store:

```sql
CREATE TABLE platform_personas (
  wr_persona_id   TEXT PRIMARY KEY,   -- ULID assigned by platform
  pg_persona_id   TEXT NOT NULL,       -- PG's internal persona_id
  pool_id         TEXT NOT NULL,
  dossier         JSONB NOT NULL,      -- full dossier verbatim
  pqs_score       FLOAT,
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 5. Forge integration

### 5.1 Persona sourcing

Forge currently sources personas from IRIS's pool via `pool_client.py`
(`GET {WR_POOL_URL}/internal/pool/sample`). On the Core Platform, Forge
calls the unified pool service instead — same endpoint pattern, same response
shape. The `WR_POOL_URL` env var simply points at the platform's pool service.

No code change in Forge's exposure engine or scoring — only the pool source
changes.

**The shared pool rule:**  
When `USE_SHARED_POOL=true` (default), Forge must use the platform pool.
`USE_SHARED_POOL=false` is reserved for local dev only. There is no
silent fallback to local generation — `PoolError` must surface.

### 5.2 Concept test → persona generation flow

```
Forge: POST /tests/{id}/run
        │
        ├── Resolve audience pool
        │     ├── pool exists + ready?  → sample from pool
        │     └── no pool?             → POST /internal/pools/generate (n=10, core)
        │                                 wait for ready (poll 15s, timeout 10min)
        │
        ├── Sample n personas for this run
        │
        ├── run_all_personas() — exposure engine
        │     (build_system_prompt per persona, 1 Haiku call per persona)
        │
        └── compute_scorecard() → verdict
```

### 5.3 Forge persona spec mapping

Forge's internal `PersonaSpec` model maps from the platform dossier:

```python
PersonaSpec(
    wr_persona_id   = dossier_row["wr_persona_id"],
    persona_id      = dossier_row["wr_persona_id"],  # use platform ID as primary
    age             = dossier["demographic_anchor"]["age"],
    gender          = dossier["demographic_anchor"]["gender"],
    city_tier       = dossier["demographic_anchor"]["location"].get("city_tier", 1),
    market          = pool["market"],
    segment         = pool["segment"],
    category_usage  = dossier["attributes"].get("category_usage", "regular_user"),
    dossier         = dossier,  # pass full dossier through to exposure engine
)
```

### 5.4 Archetype diversity enforcement

Forge must enforce a maximum of 2 personas per `decision_archetype` in any
test run panel. `decision_archetype` is derived from `derived_insights.decision_style`:

```python
STYLE_TO_ARCHETYPE = {
    "analytical":    "optimizer",
    "intuitive":     "explorer",
    "social":        "social_validator",
    "habitual":      "habitual",
    "value-driven":  "budget_constrained",
    "aspirational":  "identity_driven",
}
```

When sampling from the pool, apply the cap before finalising the panel.
See LEARNINGS_FOR_IRIS_FORGE §2.6: skewed archetypes produce skewed verdicts.

---

## 6. Shared services

Both IRIS and Forge on the platform share three services. These are unchanged
from the current WR Dashboard hub pattern.

### 6.1 Auth — WR Identity

Auth flows through `wr_identity_auth.py` (already in Forge). The platform
uses the same WR Identity service.

```python
# On any platform endpoint that touches persona data:
from wr_identity_auth import WRIdentityClaims, require_wr_identity
```

Env vars:
```
WR_IDENTITY_URL=https://wr-identity.railway.app
WR_IDENTITY_SECRET=<shared secret>
```

### 6.2 Billing

Billing flows through `wr_billing.py` (already in Forge). Credit debit
happens at the pool generation step, not at sampling.

```python
from wr_billing import check_and_debit, InsufficientCredits, NotEntitled
```

**Credit schedule (Core tier):**

| Action | Credits |
|--------|---------|
| Pool generation (Core, per persona) | 12 credits |
| Pool generation (Complete, per persona) | 18 credits |
| IRIS test run (per persona exposed) | 2 credits |
| Forge concept test run (per persona) | 2 credits |

Env vars:
```
WR_DASHBOARD_URL=https://wr-dashboard.railway.app
WR_INTERNAL_SECRET=<secret>
```

### 6.3 Memory

Cross-session persona memory (IRIS verbatims, Forge reactions) is stored
keyed on `wr_persona_id`. This lets IRIS surface "Karen has reacted to 3
of your concepts" across sessions and tests.

Env vars:
```
WR_MEMORY_URL=https://wr-memory.railway.app
WR_MEMORY_SECRET=<secret>
```

---

## 7. Env vars — complete list

Set on the Core Platform deployment (Railway / Fly.io).

### Persona Generator / Engine

```
ENGINE_URL=https://simulatte-engine.railway.app
ENGINE_SECRET=<engine bearer token>
PG_REGISTRY_PATH=/mnt/pg_registry        # Railway volume path
PG_PIPELINE_MODE=deep                    # "deep" (Core) | "simulation-ready" (Complete)
```

### PQS gates (override for dev/debug)

```
PQS_PERSONA_FLOOR=60
PQS_COHORT_FLOOR=65
PQS_WARN_THRESHOLD=75
PQS_MAX_QUARANTINE_PCT=0.20
```

### Platform pool service

```
POOL_OVERSIZE_FACTOR=1.2     # request n × factor to buffer PQS quarantines
POOL_TIMEOUT_SECONDS=1200    # 20 min — matches Engine's generation window
POOL_POLL_INTERVAL=15        # seconds between Engine job status polls
```

### Auth / billing / memory

```
WR_DASHBOARD_URL=https://wr-dashboard.railway.app
WR_INTERNAL_SECRET=<secret>
WR_IDENTITY_URL=https://wr-identity.railway.app
WR_MEMORY_URL=https://wr-memory.railway.app
```

### IRIS + Forge (unchanged from current)

```
USE_SHARED_POOL=true
FORGE_API_KEY=<key>
DATABASE_URL=<platform postgres>
```

---

## 8. Error handling contract

### PQS gate failure

When Engine returns a PQS failure, the platform pool service must:
1. Set `pool.status = "failed"`, `pool.error = <PQS message>`
2. NOT retry silently with a lower threshold
3. Surface the error verbatim to IRIS/Forge: `"Persona quality gate failed: <dimension breakdown>"`
4. User-facing message: *"Audience generation failed quality checks.
   This usually means the brief is too generic. Try adding a more specific
   category or business context."*

### Engine timeout

Engine has a 20-minute hard timeout. If the pool service doesn't receive a
response in 21 minutes:
1. `pool.status = "failed"`, `pool.error = "Engine timeout after 20 min"`
2. Send `Retry-After: 300` if IRIS/Forge retries immediately
3. Notify via webhook if registered

### Partial delivery

If Engine returns fewer personas than requested (n_delivered < n_requested):
- If `n_delivered >= n_requested × 0.80`: `pool.status = "partial"` — usable
- If `n_delivered < n_requested × 0.80`: `pool.status = "failed"`

---

## 9. Data flow — end-to-end sequence

### IRIS — new test with fresh audience

```
User: "Create test for LittleJoys ad, urban mothers 25-40, India, n=10"
         │
         ▼
Platform: POST /internal/pools/generate
  { n_personas: 12, market: "IN", age_min: 25, age_max: 40,
    domain: "cpg", pipeline_mode: "core" }
         │
         ▼
Engine: POST /generate → PG full Core pipeline (×12 personas, ~4 min)
  PQS Gate A: per-persona floor 60
  PQS Gate B: cohort floor 65
         │
         ▼ (9-12 personas returned after PQS gating)
Platform: assign wr_persona_id per persona, persist to platform_personas
pool.status = "ready", pool.n_delivered = 10
         │
         ▼
IRIS: poll detects ready → show pre-flight reveal (name, archetype, anchor)
User confirms panel → run exposure loop (build_system_prompt per persona)
         │
         ▼
IRIS: store reaction + memory event keyed on wr_persona_id
IRIS: compute scorecard → render Attention / Comprehension / Intent scores
```

### Forge — concept test drawing from existing pool

```
Forge test: audience_pool_id = "pool_01JXXXXXXXX" (already ready)
         │
         ▼
Forge: GET /internal/pools/{pool_id}/sample?n=5
  (archetype diversity enforced — max 2 per archetype)
         │
         ▼
Forge: run_all_personas() → compute_scorecard()
  (build_system_prompt per persona, 1 Haiku call per persona)
         │
         ▼
Forge: store reaction keyed on wr_persona_id
  → WR Memory gets: "wrp_01J... reacted to concept X: BUY"
  → IRIS can surface: "This persona bought 1 of 3 concepts tested"
```

---

## 10. What NOT to build

These are the anti-patterns from Litmus that the platform must explicitly
avoid. See `LEARNINGS_FOR_IRIS_FORGE.md` for the full context.

| Anti-pattern | Correct approach |
|---|---|
| Generate personas per-test-run (stateless) | Generate per-pool, reuse across tests via registry |
| Anonymous verdicts ("3 of 5 said X") | Named persona attribution on every quote |
| Soft-score demographic categoricals (age, gender) | Hard-filter on categoricals, soft-score continuous traits |
| Silent fallback to local generation | Raise `PoolError`, surface to user |
| Any persona below PQS 60 in a test | Gate A quarantines them before they reach the test |
| "Any" ICP dimension scores 1.0 | Exclude "any" dimensions from both numerator and denominator |
| Same decision archetype for 4+ of 5 personas | Enforce max 2 per archetype at sample time |
| Retry with lower PQS threshold on failure | Fix the brief (more specific domain/context) |
| Re-assign persona IDs after pool sampling | `wr_persona_id` is immutable once assigned |

---

## 11. Open questions / decisions needed

| # | Question | Default if not decided |
|---|---|---|
| 1 | Does the platform maintain one shared pool per ICP, or per-product pools? | Shared pool — IRIS and Forge draw from same pool when ICP matches |
| 2 | Is pool reuse cross-workspace or within-workspace? | Within-workspace only (privacy boundary) |
| 3 | What is the pool TTL before personas are considered stale and regenerated? | 30 days |
| 4 | Does Forge's `/tests/{id}/ask` (ask a persona a question) go through the platform pool or directly to the dossier? | Platform pool — ensures memory events are recorded |
| 5 | Railway volume for `PG_REGISTRY_PATH` — shared with Engine or platform-local? | Engine's Railway volume — platform reads via pool service, not directly |
