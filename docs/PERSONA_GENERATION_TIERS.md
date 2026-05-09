# Persona Generation Tiers

**Last updated:** 2026-05-09

Simulatte operates three distinct persona generation modes. Every surface —
The Mind, WR Populations, PopScale, Niobe — should use the **Core** tier by
default. Only escalate to Complete when agent-based simulation is required.

---

## Quick reference

| | Swift | Core | Complete |
|---|---|---|---|
| **Purpose** | Rapid prototype / UI preview | All production use-cases | Agent-based simulation |
| **Time / persona** | ~30 s | ~3 min | ~4–5 min |
| **Cost / persona** | ~$0.002 | ~$0.012 | ~$0.018 |
| **LLM calls** | 2 parallel Haiku | ~5 sequential (Sonnet) | ~5 + embedding seeding |
| **PQS gate** | Not enforced | ≥ 60 per-persona, ≥ 65 cohort | ≥ 65 per-persona, ≥ 70 cohort |
| **Entry point** | `_generate_persona_direct()` in `pilots/the-mind/api/main.py` | `invoke_persona_generator_sync(brief)` — mode="deep" | Same, mode="simulation-ready" |

---

## Tier 1 — Swift

### What it is
Two parallel Haiku API calls that run simultaneously and whose outputs are
merged. No sequential dependency chain. Returns a persona in under 30 seconds.

### Implementation
`pilots/the-mind/api/main.py` → `_generate_persona_direct()`

Call 1 (Haiku, parallel): demographics, personality traits, behavioural
surface signals.

Call 2 (Haiku, parallel): decision style, trust orientation, objection sketch.

Results merged via `_merge_persona_parts()`.

### Output fields populated
- `demographic_anchor` (name, age, gender, location, employment, education)
- `derived_insights` (decision_style, trust_anchor, risk_appetite, key_tensions)
- `behavioural_tendencies` (price_sensitivity band, switching_propensity, objection_profile — shallow)
- Basic `narrative` (first_person, third_person — often < 80 words each)

### Fields NOT populated
- `life_stories` — absent
- `memory.core.life_defining_events` — absent
- `memory.core.relationship_map` — absent
- `memory.core.immutable_constraints` — absent
- `decision_bullets` — absent
- `self_model`, `symbolic_meanings`, `attachment_profile`, `emotional_failure_modes` — absent
- `memory.working` (seed memories for simulation) — absent

### Where it is used today
- The Mind conversational interface (rapid persona load)

### When to use
Only for **instant previews** where the user is browsing personas and hasn't
committed to a study. Not appropriate for any decision or research output.

---

## Tier 2 — Core ✦ DEFAULT

### What it is
The full identity construction pipeline (`IdentityConstructor.build()`) running
in `mode="deep"`, followed by cohort assembly. Produces research-grade personas
with complete identity, memory, and behavioural structure.

This is **the default for all Simulatte features.** Upgrade to Complete only
when you need agent simulation.

### Implementation
`src/generation/identity_constructor.py` → `IdentityConstructor.build()`

Invoked via: `invoke_persona_generator_sync(brief)` with `mode="deep"` (the
existing WR Populations path).

### Pipeline steps

| Step | Phase | What happens |
|------|-------|--------------|
| 1 | `attribute_fill` | LLM fills all taxonomy attributes for the domain |
| 2 | `identity_core` | Derived insights computed (decision style, risk, tensions, coping) |
| 3 | `life_story` | LLM generates 2–3 formative life story episodes |
| 4 | `identity_behavior` | Tendency estimator: price band, switching propensity, trust orientation |
| 5 | `identity_behavior` | LLM generates first-person + third-person narrative (≥ 80 words each) |
| 6 | — | Core memory assembled (identity statement, key values, relationship map, constraints) |
| 6b | — | Authoritative core memory re-assembled via `assemble_core_memory()` |
| 7 | — | Persona validated (G1/G2/G3 individual gates) |
| — | cohort | `assemble_cohort()`: worldview, distinctiveness, type coverage, G6–G12 gates |

### Output fields populated
All fields except `memory.working.seed_memories` (used by agent simulation only).

Full list: `demographic_anchor`, `life_stories`, `attributes`, `derived_insights`,
`behavioural_tendencies`, `narrative`, `decision_bullets`, `memory.core`
(identity_statement, key_values, life_defining_events, relationship_map,
immutable_constraints, tendency_summary), `cohort_summary`.

### PQS gate
Per-persona minimum: **60 / 100**. Cohort minimum: **65 / 100**.
Personas below threshold are regenerated (up to `max_retries_per_persona`).
Cohorts below threshold abort with an actionable error message.

### Where it is used today
- WR Populations (via `simulatte-engine` → `invoke_persona_generator_sync`)

### Where it should be used (rollout target)
- **The Mind** — replace Swift as the load path (async background generation,
  serve Swift version immediately, upgrade to Core on completion)
- **PopScale** — all concept test panels
- **Niobe** — all survey cohorts
- **Benchmark** — the persona being evaluated must be Core-grade

---

## Tier 3 — Complete

### What it is
Core plus seed working memory (OpenAI embedding-based). Required when personas
must act as autonomous agents in a multi-turn social simulation.

### Additional step vs Core

| Step | What happens |
|------|--------------|
| 7 | `bootstrap_seed_memories()` — seeds 6–12 episodic working memories from core memory events using text-embedding-3-small. Populates `memory.working` for agent loop. |

### Implementation
Same entry point as Core: `invoke_persona_generator_sync(brief)` with
`mode="simulation-ready"`.

### When to use
- Multi-agent Niobe simulation panels
- PopScale social diffusion runs (social topology enabled)
- Any feature that calls `persona.memory.working` at runtime

### Extra cost
~$0.006/persona on top of Core (OpenAI embedding calls + additional Anthropic
tokens for memory reflection seeding).

### PQS gate
Per-persona minimum: **65 / 100**. Cohort minimum: **70 / 100**.

---

## Routing decisions

```
New persona needed
│
├── Need it in < 60s? (UI preview only, no study output)
│   └── Swift
│
├── Multi-agent simulation / social topology?
│   └── Complete  (mode="simulation-ready")
│
└── Everything else  ← 95% of cases
    └── Core  (mode="deep")  ✦ DEFAULT
```

---

## Making Core the default

### The Mind (current gap)
The Mind currently uses Swift for all personas. Recommended path:

1. On persona request: serve Swift persona immediately (existing 30s path)
2. Immediately queue a background Core generation for the same ICP
3. When Core completes: swap persona in DB, emit a WebSocket/SSE event so
   the UI upgrades the loaded persona without page reload
4. PQS gate enforced on the Core persona before swap

This gives the UX of instant load with the quality of Core for all subsequent
conversations.

### env var override
Set `PG_PIPELINE_MODE=simulation-ready` to force Complete globally (e.g. for
a simulation-heavy deployment). Default is `deep` (Core).

---

## How to invoke PQS manually

```python
from src.quality.pqs import compute_pqs_from_dict, format_pqs_summary

# cohort is any raw dict with a "personas" list (from cohort JSON file)
import json
cohort = json.load(open("outputs/my_cohort.json"))

report = compute_pqs_from_dict(cohort)
print(format_pqs_summary(report))
# → [PQS] ████████████░░░░░░░░  62.4/100  (N=10)
# → [PQS]   Behavioral Realism:  58.0  |  Identity Depth:  71.2
# → [PQS]   Decision Quality:    55.3  |  Cohort Health:   64.8
```

```python
# Per-persona scores are inside the report dict
for pid, score in report["components"].items():
    print(pid, score)
# Access per-persona from the full compute_pqs() (Pydantic envelope):
from src.quality.pqs import compute_pqs
pqs_report = compute_pqs(envelope_obj)
for pid, score in pqs_report.persona_scores.items():
    print(f"  {pid}: {score:.1f}")
```

From the CLI (quick check on an existing cohort file):
```bash
python3 -c "
import json
from src.quality.pqs import compute_pqs_from_dict, format_pqs_summary
cohort = json.load(open('outputs/cohort_abc123.json'))
print(format_pqs_summary(compute_pqs_from_dict(cohort)))
"
```
