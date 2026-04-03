# Multi-Agent Social Simulation — Architecture Design
**Status:** APPROVED — Sprint SA ready to start
**Author:** Tech Lead (Claude)
**Date:** 2026-04-03
**Spec anchor:** Master Spec §14B (Open Research Questions — OASIS social simulation, deferred to v2)
**Constitution check:** All decisions verified against P1, P2, P3, P4, P10

---

## Prerequisites

`calibration_state.status != "uncalibrated"` on the target cohort before running social simulation. For LittleJoys this is already satisfied (`benchmark_calibrated` as of Sprint 22).

---

## Critical Distinction: Peer Influence vs. Social Media Influence

**This toggle controls peer-to-peer influence only.**

Social media stimuli (Instagram ads, influencer posts, sponsored content) are **not** peer influence — they are standard stimuli that already flow through `perceive()` regardless of this toggle. A persona encountering an Instagram ad is just a `stimulus_type: "brand_touchpoint"` event processed by the existing cognitive loop. That always happens.

What this toggle controls is whether **Persona A's decision or expressed opinion influences Persona B's reasoning**. This is peer-level social contagion — word of mouth, community decisions, group dynamics. When the toggle is `ISOLATED`, each persona reasons entirely from their own observations and the stimuli they receive. No persona learns what another persona decided.

```
Toggle OFF (ISOLATED):
  Persona A sees Instagram ad → perceives it → decides independently
  Persona B sees Instagram ad → perceives it → decides independently
  Neither knows what the other decided.

Toggle ON (MODERATE):
  Persona A sees Instagram ad → decides
  Persona B sees Instagram ad + hears "Priya (someone you know) just switched brands" → decides
  Priya's expressed decision is now an input to B's reasoning.
```

The `SocialSimulationLevel` enum maps directly to this toggle:
- `ISOLATED` = peer influence OFF (default — existing system behaviour)
- Any other level = peer influence ON, with graduated intensity

---

## Core Principle

Social influence flows through the **existing cognitive loop unchanged**. It arrives as a synthetic stimulus via `perceive()` — not as direct attribute mutation. At `ISOLATED` level (the default), the system behaves identically to today. Zero regression risk.

The LLM remains the cognitive engine (P2). Peer influence enters as *evidence* the LLM can accept, reject, or reweight — not as a command that overrides reasoning.

---

## 1. The Interaction Primitive

A persona does not telepathically know another persona's attribute values. It only observes their **expressed output** — a stated decision or opinion formatted as a peer stimulus:

```
"[Name], someone you know, recently said: '[expressed_position_text]'"
```

This pattern already exists in `decide.py`'s SOCIAL SIGNAL CHECK (step 4). The social layer makes it dynamic and turn-based rather than static.

The expressed position is drawn from the transmitting persona's most recent `DecisionOutput` or a summary of their `Observation` content.

---

## 2. Affected Attributes

### Never touched — constitutionally protected

- All of `demographic_anchor` (age, gender, location, household, education, employment)
- All of `life_stories`
- `memory.core.*` (identity statement, life-defining events, immutable constraints)
- `derived_insights.*` (computed deterministically — recalculation is the only valid update path)
- Tendency `band` fields (categorical — never shift)
- `behavioural_tendencies.trust_orientation.weights` (numeric weights — never shift)
- `persona_id`, `generated_at`, `generator_version`

### Temporarily mutable — working memory only (default for all levels)

Social stimuli processed via `perceive()` create entries in working memory exactly as any other stimulus would:

| Field | Type of change |
|---|---|
| `memory.working.observations` | New entries appended |
| `memory.working.reflections` | New entries when accumulator threshold fires |
| `memory.working.simulation_state.importance_accumulator` | Incremented |
| `memory.working.simulation_state.consideration_set` | Updated by `decide()` |
| `memory.working.brand_memories` | Updated if stimulus is brand-related |

### Conditionally mutable — tendency descriptions only (HIGH level, opt-in)

The `description` prose fields within `behavioural_tendencies` may shift under sustained social influence. This is the most consequential design choice.

**Conditions required (all must be met):**
1. `SocialSimulationLevel >= HIGH` (0.75)
2. ≥ 3 social reflections consistently pointing in the same direction
3. A `TendencyShiftRecord` audit entry created (P10)
4. The categorical `band` field never changes

**Fields that may shift:**

| Field | Shift condition |
|---|---|
| `behavioural_tendencies.trust_orientation.description` | ≥ 3 social reflections citing changed peer trust signals |
| `behavioural_tendencies.switching_propensity.description` | ≥ 3 social reflections referencing peer switching behaviour |
| `behavioural_tendencies.price_sensitivity.description` | ≥ 3 social reflections referencing peer price reactions |

**Fields that never shift regardless of level:**
- Any tendency `band` field
- `trust_orientation.weights` (numeric)
- `trust_orientation.dominant`
- `objection_profile`
- All of `derived_insights`

---

## 3. The Control Variable — `SocialSimulationLevel`

```python
class SocialSimulationLevel(str, Enum):
    ISOLATED   = "isolated"    # 0.0 — no social influence. Existing behaviour unchanged.
    LOW        = "low"         # 0.25 — weak peer signals only
    MODERATE   = "moderate"    # 0.50 — standard social simulation
    HIGH       = "high"        # 0.75 — strong peer influence; tendency drift allowed
    SATURATED  = "saturated"   # 1.0  — maximum echo chamber risk; research/stress-test only
```

The level is a **gate multiplier** applied to the `importance` score of each synthetic social stimulus before it enters `perceive()`:

```python
gated_importance = max(1, round(raw_importance × level_weight))
# ISOLATED (0.0): all social stimuli suppressed — never injected
# LOW (0.25):     importance range 1–3
# MODERATE (0.50): importance range 3–6
# HIGH (0.75):    importance range 5–8
# SATURATED (1.0): full importance, no dampening
```

### "Reduce" vs "Enhance" — what changes per attribute

| Attribute | Reducing level (→ ISOLATED) | Enhancing level (→ HIGH/SATURATED) |
|---|---|---|
| `trust_orientation.description` | Stays static; entirely internally derived | May soften if peers demonstrate different trust patterns ≥ 3 times |
| `consideration_set` | Only self-generated options | Peer-mentioned alternatives enter more readily |
| Social observation importance | Low (1–3); rarely triggers reflection | High (5–8); often triggers reflection and influences decisions |
| Tendency description drift | Never occurs | Occurs after ≥ 3 aligned social reflections at HIGH level |
| `decide.py` step 4 social check | Static `primary_decision_partner` only (existing behaviour) | Live peer positions from current simulation turn injected |

---

## 4. Susceptibility and Signal Strength

### Receiver susceptibility — who gets influenced

All fields drawn from existing `PersonaRecord` schema:

| Field | Path | Weight |
|---|---|---|
| `social_proof_bias` | `attributes["social"]["social_proof_bias"].value` | 0.40 |
| `trust_orientation.peer` | `behavioural_tendencies.trust_orientation.weights.peer` | 0.30 |
| `wom_receiver_openness` | `attributes["social"]["wom_receiver_openness"].value` | 0.30 |

```python
base_susceptibility = (
    social_proof_bias * 0.40 +
    trust_orientation_peer * 0.30 +
    wom_receiver_openness * 0.30
)
consistency_dampener = consistency_score / 100.0  # firm personas resist influence
style_modifier = +0.10 if decision_style == "social" else (
                 -0.10 if decision_style == "analytical" else 0.0)

susceptibility = clamp(
    base_susceptibility * (1.0 - 0.5 * consistency_dampener) + style_modifier,
    0.0, 1.0
)
```

### Transmitter signal strength — how loud the signal is

| Field | Weight |
|---|---|
| `derived_insights.decision_style_score` | 0.50 |
| `derived_insights.consistency_score / 100` | 0.50 |

```python
signal_strength = decision_style_score * 0.50 + (consistency_score / 100.0) * 0.50
```

### Computing gated importance

```python
raw_importance = round(susceptibility_B * signal_strength_A * 10)  # 1–10 scale
gated_importance = max(1, round(raw_importance * level_weight))
```

These are **soft prior computations only** — they set the importance of the synthetic stimulus. The LLM still reasons through whether to accept, reject, or reweight the peer signal (P4 compliant).

---

## 5. Network Topologies

| Topology | Description | Best for |
|---|---|---|
| `FULL_MESH` | Every persona ↔ every other persona | N ≤ 5, group decisions |
| `RANDOM_ENCOUNTER` | Each turn, each persona paired with K random others | N = 10–20, market simulation |
| `DIRECTED_GRAPH` | Explicit edges with types (peer/authority/family/influencer) and weights | Opinion leaders, formal social structures |

Default when social level > ISOLATED and no explicit network provided: `RANDOM_ENCOUNTER`.

---

## 6. Simulation Loop Integration

Social influence fires **between stimuli** — it is an inter-turn event, not intra-turn. It slots in as a new Step 0 before `perceive()` on each turn:

```
Turn T:
  Step 0: InfluenceEngine.generate_influence_events(cohort_states, network, level, turn)
          → list[SocialInfluenceEvent] (empty list at ISOLATED)

  For each persona P:
    → For each SocialInfluenceEvent targeting P:
         format as synthetic stimulus string
         perceive(synthetic_stimulus, P) with gated_importance
         write_observation → increment_accumulator as normal

    → perceive(primary_stimulus, P) as today

    → (conditional) reflect — now informed by both social + primary observations

    → (conditional) promote — unchanged

    → (conditional) decide — step 4 SOCIAL SIGNAL CHECK now references
       live peer observations naturally via retrieved memories

    → (HIGH level only) InfluenceEngine.check_tendency_drift(P)
```

**Critical:** This requires **zero changes** to `perceive.py`, `reflect.py`, `decide.py`, or `working_memory.py`. The social influence system is an envelope around the existing loop.

---

## 7. New Files

```
src/social/
  __init__.py
  schema.py              ← SocialInfluenceEvent, InfluenceVector, TendencyShiftRecord,
                            SocialSimulationTrace, SocialNetwork, SocialNetworkEdge,
                            NetworkTopology, SocialSimulationLevel
  influence_engine.py    ← InfluenceEngine (stateless orchestrator):
                            generate_influence_events(), format_as_stimulus(),
                            check_tendency_drift()
  network_builder.py     ← build_full_mesh(), build_random_encounter()
  loop_orchestrator.py   ← run_social_loop() wraps run_loop(); never modifies it
  trace_builder.py       ← accumulates SocialInfluenceEvents → SocialSimulationTrace
  tendency_drift.py      ← apply_tendency_drift() via model_copy
  validity.py            ← SV1–SV5 gate functions
```

**Modified files (only):**
- `src/experiment/session.py` — two new optional fields:
  ```python
  social_simulation_level: SocialSimulationLevel = SocialSimulationLevel.ISOLATED
  social_network: SocialNetwork | None = None
  ```
- `src/cli.py` — `--social-level` and `--social-topology` flags

Nothing else touched.

---

## 8. Key Data Structures

### `SocialInfluenceEvent`
```python
class SocialInfluenceEvent(BaseModel):
    event_id: str
    turn: int
    transmitter_id: str
    receiver_id: str
    edge_type: Literal["peer", "authority", "family", "influencer"]
    expressed_position: str
    source_output_type: Literal["decision", "observation"]
    raw_importance: int
    gated_importance: int
    level_weight_applied: float
    susceptibility_score: float
    signal_strength: float
    synthetic_stimulus_text: str
    resulting_observation_id: str | None
    timestamp: datetime
```

### `TendencyShiftRecord` (audit trail for any description drift)
```python
class TendencyShiftRecord(BaseModel):
    record_id: str
    persona_id: str
    session_id: str
    turn_triggered: int
    tendency_field: str                      # e.g. "trust_orientation.description"
    description_before: str
    description_after: str
    source_social_reflection_ids: list[str]  # ≥ 3 required
    social_simulation_level: SocialSimulationLevel
    timestamp: datetime
```

### `SocialSimulationTrace`
```python
class SocialSimulationTrace(BaseModel):
    trace_id: str
    session_id: str
    cohort_id: str
    social_simulation_level: SocialSimulationLevel
    network_topology: NetworkTopology
    total_turns: int
    total_influence_events: int
    influence_vectors: dict[str, InfluenceVector]
    tendency_shift_log: list[TendencyShiftRecord]
    validity_gate_results: dict[str, Any]
    generated_at: datetime
```

---

## 9. Validity Gates

New gates for any run with `SocialSimulationLevel != ISOLATED`:

| Gate | Check | Threshold |
|---|---|---|
| SV1 | Every `SocialInfluenceEvent` has a matching `resulting_observation_id` in receiver's working memory | 100% |
| SV2 | Decision diversity under social influence | No single decision > 80% (tighter than S2's 90%) at HIGH level |
| SV3 | Echo chamber detection: single-transmitter concentration | Warn > 0.60, Fail > 0.80 |
| SV4 | Tendency shift direction consistent with cited reflections | Manual review at v1 |
| SV5 | `derived_insights` unchanged (deterministic fields never drifted) | Exact match on recompute |

### Echo chamber score
```python
echo_chamber_score = max_influence_events_from_single_transmitter / total_influence_events
# > 0.60 → SV3 warning
# > 0.80 → SV3 failure → recommend reducing SocialSimulationLevel or switching to DIRECTED_GRAPH
```

---

## 10. Anti-Patterns Guarded

| Anti-pattern | Guard |
|---|---|
| A1 (Coefficient creep) | `susceptibility_score` and `signal_strength` set importance only — they do not pre-compute "probability of attitude change." LLM reasons through the change. |
| A2 (Sycophancy at population level) | SV3 echo chamber gate detects false consensus. `SATURATED` level is stress-test only, never production default. |
| Social pressure overriding reasoning | Peer influence enters via `perceive()` as evidence, not via direct attribute mutation. `decide.py` step 3 (constraint check) and step 1 (gut reaction) are not bypassed. |
| Tendency drift without audit | Any session modifying a `description` field must produce a `TendencyShiftRecord`. `check_tendency_drift()` runs in audit mode at all levels. |

---

## 11. Sprint Plan (3 sprints)

### Sprint SA — Schema + InfluenceEngine + NetworkBuilder
**Gate to start:** `calibration_state.status != "uncalibrated"` on target cohort ✅ (LittleJoys already benchmark_calibrated)

| Engineer | Deliverable |
|---|---|
| Cursor | `src/social/__init__.py`, `src/social/schema.py`, `src/experiment/session.py` extension |
| Codex | `src/social/influence_engine.py` — `generate_influence_events()`, `format_as_stimulus()`, `check_tendency_drift()`, susceptibility/signal_strength computation |
| Goose | `src/social/network_builder.py` — `build_full_mesh()`, `build_random_encounter()` |
| Antigravity | `tests/test_social/test_schema.py` (10+ tests), `test_influence_engine.py` (12+ tests), `test_network_builder.py` (8+ tests) |

Acceptance: ISOLATED level always returns `[]`; susceptibility in [0, 1]; gated importance in [1, 10]; `ExperimentSession` default is ISOLATED; existing tests pass unchanged.

---

### Sprint SB — Loop Orchestrator + Trace Pipeline + Validity Gates + CLI
**Gate to start:** Sprint SA passes.

| Engineer | Deliverable |
|---|---|
| Cursor | `src/social/loop_orchestrator.py` — `run_social_loop()` wraps `run_loop()`; never modifies it |
| Codex | `src/social/trace_builder.py`, `src/social/tendency_drift.py` |
| Goose | `src/social/validity.py` — SV1–SV5 gate functions |
| OpenCode | `src/cli.py` — `--social-level` and `--social-topology` flags |
| Antigravity | `tests/test_social/test_integration.py` — 2-persona cohort, MODERATE level, end-to-end |

Acceptance: `run_loop()` signature unchanged; social observations appear in receiver's `working.observations`; `SocialSimulationTrace` populated; all SV1–SV5 gates produce results.

---

### Sprint SC — Empirical Validation + Spec Updates
**Gate to start:** Sprint SB passes.

Focus: no new features. Runs SVB1 (social stability), SVB2 (memory faithfulness), SVB3 (echo chamber stress test). Tunes susceptibility formula coefficients based on SVB1 results. Updates `SIMULATTE_VALIDITY_PROTOCOL.md` with Module 6 (Social Simulation Gates). Updates master spec with Settled Decision S28.

---

## 12. Pre-Implementation Constitution Check

- [x] No numerical parameters added to `PersonaRecord` — susceptibility and signal_strength are ephemeral, not stored
- [x] LLM remains cognitive engine — social influence enters via `perceive()`, not attribute mutation (P2)
- [x] Memory not deferred — social layer feeds through existing memory architecture (P3)
- [x] Core memory immutable — social simulation cannot trigger core memory promotion (S17)
- [x] Domain-agnostic — no domain-specific logic in social layer (P8)
- [x] Every influence event carries a `SocialInfluenceEvent` record (P10)
- [x] Tendency shifts require `TendencyShiftRecord` with source citations (P10)
- [x] `run_loop()` signature unchanged — existing tests pass at ISOLATED level

---

## Sign-Off Required Before Sprint SA Starts

**Tech Lead approval needed on:**
1. Control variable scale — is 5-level enum (ISOLATED/LOW/MODERATE/HIGH/SATURATED) the right granularity, or do you want a continuous 0–1 float?
2. Tendency drift conditions — is the ≥ 3 social reflections threshold right, or should it be higher/lower?
3. Network topology defaults — RANDOM_ENCOUNTER as default for N > 5 personas, or should the user always specify explicitly?
4. Sprint sequencing — SA → SB → SC is the proposed order. Any changes?
