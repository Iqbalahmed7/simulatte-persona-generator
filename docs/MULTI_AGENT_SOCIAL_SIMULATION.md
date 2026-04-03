# Multi-Agent Social Simulation — Architecture Specification

**Status:** Canonical. Updated through Sprint SC (2026-04-03).
**Sprints:** SA (schema + engine + network) · SB (orchestrator + trace + validity + CLI) · SC (empirical calibration)

---

## §1 — Design Principles

| ID | Principle |
|---|---|
| P2 | **LLM is the cognitive engine.** All social influence computations are deterministic. Social evidence enters only through `perceive()` as stimulus text. The LLM retains full authority to accept, reject, or reframe it. |
| P4 | **LLM can accept/reject.** Synthetic stimuli produced by `format_as_stimulus()` are injected via `run_loop()` unchanged. |
| P10 | **Traceability.** Every influence event carries a full audit trail. Every validity gate result is stored in `SocialSimulationTrace`. |

---

## §2 — Tendency Drift

Tendency drift refers to the gradual change in a persona's description-level priors due to repeated social influence exposure. Three fields are driftable:

- `trust_orientation.description`
- `switching_propensity.description`
- `price_sensitivity.description`

**Band fields (`band`, `weights`, `dominant`, `source`) NEVER change through drift.** Only prose descriptions may evolve.

Detection is via `check_tendency_drift()` in `influence_engine.py`. Application is via `apply_tendency_drift()` in `tendency_drift.py` using a three-level `model_copy` chain.

Drift application conditions: level ≥ HIGH and ≥ 3 social reflections in working memory.

---

## §3 — Gated Importance

Gated importance controls how strongly a social stimulus is prioritised in the receiver's perception loop.

```
raw_importance = max(1, round(susceptibility × signal_strength × 10))  # [1, 10]
gated_importance = max(1, round(raw_importance × level_weight))         # [1, 10]
```

At ISOLATED (weight=0.0), `generate_influence_events()` returns `[]` before this formula is reached.

---

## §4 — Formulas (Calibrated Sprint SC)

### Susceptibility (receiver)

```
base = social_proof_bias × 0.40
     + trust_orientation.weights.peer × 0.30
     + wom_receiver_openness × 0.30

consistency_dampener = consistency_score / 100.0
style_modifier = +0.10 if decision_style == "social"
               | -0.10 if decision_style == "analytical"
               | 0.0   otherwise

susceptibility = clamp(base × (1.0 − 0.5 × dampener) + style_modifier, 0.0, 1.0)
```

Fallback: if persona has no "social" attribute category, `social_proof_bias` and `wom_receiver_openness` default to 0.5.

**SVB1 empirical result (Sprint SC, N=243):** mean=0.319, stdev=0.165, range=[0.0, 0.829], 4 floor clamps (1.6%), 0 ceiling clamps. No systematic bias. Formula confirmed — no tuning required.

### Signal Strength (transmitter)

```
signal_strength = decision_style_score × 0.50
                + (consistency_score / 100.0) × 0.50
```

**SVB2 empirical result (Sprint SC, N=25):** mean=0.515, stdev=0.212, range=[0.10, 0.925]. Full range covered, good variance. No tuning required.

---

## §5 — Social Simulation Levels

| Level | Weight | Behaviour |
|---|---|---|
| ISOLATED | 0.00 | Default. `generate_influence_events()` returns `[]` immediately. Zero overhead. |
| LOW | 0.25 | Weak peer influence; importance heavily dampened. |
| MODERATE | 0.50 | Balanced social influence. Recommended for most research scenarios. |
| HIGH | 0.75 | Strong peer influence. SV2 tightens to 80% diversity threshold. |
| SATURATED | 1.00 | Maximum peer influence. SV2 tightens to 80% diversity threshold. |

---

## §6 — Orchestration Architecture

`run_social_loop()` in `loop_orchestrator.py` is the entry point for multi-persona simulations.

Per-turn execution order:

```
Turn T:
  Step 0: generate_influence_events(cohort, network, level, T, prior_decisions)
          → [] at T=0 (no prior decisions exist yet)
  Step 1: for each social event targeting persona P:
            run_loop(event.synthetic_stimulus_text, P)
            link loop_result.observation.id → event.resulting_observation_id
  Step 2: for each persona P:
            run_loop(stimuli[T], P, decision_scenario=...)
            collect P.decision.decision → prior_decisions[P.id] for T+1
  Step 3: trace_builder.accumulate(all step-1 events)
```

`run_loop()` is called with no modifications to its signature or internals.

---

## §7 — Network Topologies

| Topology | Builder | Echo Chamber Score Formula |
|---|---|---|
| FULL_MESH | `build_full_mesh(persona_ids)` | 1/N by construction |
| RANDOM_ENCOUNTER | `build_random_encounter(persona_ids, k, seed)` | ≤ k/(N−1) × 1/N (approx) |
| DIRECTED_GRAPH | `build_directed_graph(edges)` | Depends on graph structure |

**SVB3 empirical result (Sprint SC):**

| Cohort N | FULL_MESH score | RANDOM_ENCOUNTER (k=2) score | SV3 zone |
|---|---|---|---|
| 2 | 0.500 | 0.500 | PASS |
| 3 | 0.333 | 0.333 | PASS |
| 4 | 0.250 | 0.250 | PASS |
| 6 | 0.167 | 0.167 | PASS |

All standard cohort sizes pass SV3 comfortably under both topologies. Echo chamber concern arises only with highly asymmetric `DIRECTED_GRAPH` configurations (e.g. hub-and-spoke).

---

## §8 — TraceBuilder + InfluenceVector

`TraceBuilder` in `trace_builder.py` accumulates `SocialInfluenceEvent` objects across all turns and produces a `SocialSimulationTrace` after the loop completes.

Per-persona `InfluenceVector` contains:
- `total_events_transmitted` / `total_events_received`
- `mean_gated_importance_transmitted` / `mean_gated_importance_received`

Personas with no events in a given direction have mean = 0.0.

---

## §9 — Validity Gates (Confirmed Sprint SC)

All gates run after `run_social_loop()` completes. Results stored in `trace.validity_gate_results`.

| Gate | Threshold | Pass Condition | Note |
|---|---|---|---|
| SV1 | 100% linkage | All events have `resulting_observation_id` set | Vacuously true on empty events |
| SV2 | ≤80% (HIGH/SATURATED) / ≤90% (others) | No single normalised decision string exceeds threshold | Case + whitespace normalised |
| SV3 | ≤0.60 PASS / 0.60–0.80 WARN / >0.80 FAIL | `max_tx_events / total_events` | FULL_MESH: score=1/N; safe for N≥2 |
| SV4 | Manual review | Always `passed=True`; detail flags shift count | v1: automated pass, requires human review |
| SV5 | Derived insights unchanged | 6 `DerivedInsights` fields identical before/after | Fields: decision_style, trust_anchor, risk_appetite, primary_value_orientation, consistency_score, consistency_band |

**Threshold confirmation (Sprint SC):** All thresholds confirmed as appropriate based on SVB1–SVB3 empirical results. No changes to validity gate thresholds from Sprint SB.

---

## §10 — Tendency Drift Detection

`check_tendency_drift()` in `influence_engine.py` is detection-only. It returns `TendencyShiftRecord` objects with sentinel `description_after` when conditions are met.

Conditions: level ∈ {HIGH, SATURATED} AND len(social_reflections) ≥ 3.

`apply_tendency_drift()` in `tendency_drift.py` applies a confirmed shift using a three-level `model_copy` chain: tendency_obj → BehaviouralTendencies → PersonaRecord. Band fields are structurally untouched.

---

## §11 — CLI Integration

The `simulate` command in `src/cli.py` exposes:

| Flag | Values | Default |
|---|---|---|
| `--social-level` | isolated / low / moderate / high / saturated | isolated |
| `--social-topology` | full_mesh / random_encounter | random_encounter |

At `isolated` (default), behaviour is identical to pre-SA behaviour — zero overhead, full backward compatibility.

Output JSON includes a `social_simulation` metadata key:
```json
{
  "social_simulation": {
    "social_level": "moderate",
    "social_topology": "full_mesh"
  }
}
```

At `isolated`, `social_topology` is `null`.

---

## §12 — Implementation Status

| Sprint | Deliverable | Status |
|---|---|---|
| SA | schema.py, influence_engine.py, network_builder.py, session.py social fields | ✅ Complete |
| SB | loop_orchestrator.py, trace_builder.py, tendency_drift.py, validity.py, CLI flags | ✅ Complete |
| SC | SVB1–SVB3 empirical validation; formula and threshold confirmation | ✅ Complete |
