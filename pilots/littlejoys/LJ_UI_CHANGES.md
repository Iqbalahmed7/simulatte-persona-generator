# LittleJoys App — UI/UX Changes Required
## Due to Simulatte Sprint 19–23 Integration

**Owner:** Tech Lead
**Target sprint:** Sprint 23
**App location:** `/Users/admin/Documents/Simulatte Projects/1. LittleJoys/app/streamlit_app.py`

---

## Why These Changes Are Required

The LittleJoys Streamlit app was built on the legacy engine. The Simulatte v1 engine (Sprints 1–22) introduces:
- A new persona schema (`PersonaRecord` vs old `Persona`)
- A new data file (`simulatte_cohort_final.json` vs `personas_generated.json`)
- A new simulation engine (`run_loop` with tiers vs `batch_runner`)
- New per-decision outputs: `noise_applied`, `confidence` (post-noise), memory state
- New cohort-level metadata: calibration status, tier used, Sprint 19 features

The app must be updated to consume these. Changes are organized by page.

---

## Change 1: Data Source (Breaking)

**Page:** All pages
**Priority:** CRITICAL — app will not load without this

**Current behaviour:**
```python
# streamlit_app.py
candidates = [
    PROJECT_ROOT / "data" / "population" / "personas_generated.json",
    PROJECT_ROOT / "data" / "population" / "personas.json",
]
```
Loads old `Persona` objects from the legacy personas file.

**Required change:**
Load from `simulatte_cohort_final.json` (a `CohortEnvelope`) via the adapter:

```python
from pilots.littlejoys.app_adapter import load_simulatte_cohort, persona_to_display_dict

@st.cache_data
def load_all_personas() -> list[dict]:
    cohort_path = Path("/Users/admin/Documents/Simulatte Projects/1. LittleJoys/data/population/simulatte_cohort_final.json")
    personas = load_simulatte_cohort(cohort_path)
    return [persona_to_display_dict(p) for p in personas]
```

**Impact on display:**
All persona fields currently displayed (name, age, city, decision_style, trust_anchor, etc.) must be mapped in `app_adapter.persona_to_display_dict()`. No visible change to the user if mapping is correct — the persona cards look the same.

---

## Change 2: Sidebar — Calibration Status Badge (New)

**Page:** All pages (sidebar)
**Priority:** HIGH

**What to add:**
A badge in the sidebar showing the current cohort's calibration status. Reads from the `CohortEnvelope.calibration_state`.

```
┌─────────────────────────────┐
│  Cohort: littlejoys-regen   │
│  Tier: signal               │
│  ● UNCALIBRATED             │  ← amber dot + "UNCALIBRATED" text
│  Personas: 200 | Parity: 97%│
└─────────────────────────────┘
```

**Color coding:**
- `calibrated` (benchmark_calibrated or client_calibrated) → green dot
- `uncalibrated` → amber dot + tooltip: "Run --calibrate to anchor against benchmarks"
- `calibration_failed` → red dot
- `last_calibrated` > 6 months ago → amber dot + "Stale (> 6 months)"

**Implementation:** `components/calibration_badge.py` (OpenCode, Sprint 23)

---

## Change 3: Run Scenario Page — Tier Selector (New)

**Page:** Run Scenario
**Priority:** HIGH

**What to add:**
A radio button group before the "Run" button:

```
Simulation Tier
  ○ DEEP    — Sonnet reflect + decide (highest quality, slower)
  ● SIGNAL  — Haiku reflect, Sonnet decide (recommended)
  ○ VOLUME  — Haiku throughout (fastest, directional only)

  Estimated cost per run: ~$0.12 (signal tier, 200 personas × 3 stimuli)
```

**Behaviour:**
- Default selection: SIGNAL
- Selected tier is passed to `run_simulatte_batch(personas, journey_config, tier=selected_tier)`
- Cost tooltip is informational only (static text per tier)

**Implementation:** Goose adds `st.radio("Simulation Tier", ...)` to Run Scenario page in Sprint 23.

---

## Change 4: Decision Results — Confidence + Noise Display (Updated)

**Page:** Run Scenario → Results tab
**Priority:** HIGH

**Current behaviour:**
Shows `confidence: 72` as a plain number.

**Required change:**
Show `72 ± 8` where `8 = abs(noise_applied)`. Color the confidence score:
- ≥ 70 → green
- 50–69 → amber
- < 50 → red

Example row in results table:

| Persona | Decision | Confidence | Key Driver |
|---|---|---|---|
| Priya Sharma | Buy | **76 ± 5** | Pediatrician recommendation |
| Rahul Mehta | Research more | **54 ± 12** | Needs to verify ingredients |
| Ananya Patel | Buy | **81 ± 5** | Subscribe & Save pricing |

**Tooltip on hover:** "Confidence score after calibrated noise injection (±{half} range based on persona consistency score of {consistency_score})"

**Implementation:** `components/confidence_display.py` (OpenCode, Sprint 23)

---

## Change 5: Persona Explorer — Memory State Panel (New)

**Page:** Persona Explorer → individual persona view
**Priority:** MEDIUM

**What to add:**
A compact panel below the persona profile card showing memory state:

```
Memory State
  Observations:  12  (post-simulation)
  Reflections:    2
  Last reflection: "I'm noticing that authority figures — especially the
                    pediatrician — are more influential than I expected..."
  Seed memories:   3  (bootstrapped)
```

**Behaviour:**
- Show after a simulation run has been completed for this persona
- If no simulation has run: show "No simulation data yet — run a scenario to populate memory"
- Observation and reflection counts read from `PersonaRecord.memory.working`
- Last reflection = the most recent entry in `working.reflections` (by timestamp)

**Implementation:** `components/memory_state_viewer.py` (OpenCode, Sprint 23)

---

## Change 6: Persona Explorer — Consistency Score + Noise Band (Updated)

**Page:** Persona Explorer → individual persona view
**Priority:** MEDIUM

**Current behaviour:**
No consistency score displayed.

**Required change:**
Add to the persona attribute summary:

```
Decision Consistency
  Score: 74   Band: MEDIUM
  Noise range: ±12 pts on confidence scores

  This persona's decisions show moderate consistency. Confidence scores
  are perturbed by up to ±12 points to reflect realistic decision variability.
```

**Data source:** `persona.derived_insights.consistency_score`
**Noise range:** 5 if score ≥ 75, 12 if 50–74, 20 if < 50 (mirrors `_noise_range()` in `decide.py`)

---

## Change 7: Persona Explorer — Aging Status (New, post-Sprint 22)

**Page:** Persona Explorer → individual persona view
**Priority:** LOW (only relevant after run_annual_review() has been called)

**What to add:**
If a persona has been aged (i.e. if `age_report` metadata exists in session state or file), show:

```
Longitudinal Aging
  Last reviewed: 2026-04-03
  Reflections reviewed: 18
  Promotions to core: 2
  Promotions blocked: 1 (content: demographic reference)
```

**Behaviour:**
- If not aged: section hidden (no "Not yet aged" placeholder needed)
- Read from `AgingReport` saved alongside the cohort (format TBD in Sprint 22)

---

## Change 8: Business Problems Page — Simulation Quality Gates Summary (New, post-Sprint 21)

**Page:** Business Problems (home page)
**Priority:** MEDIUM (post Sprint 21)

**What to add:**
After a scenario run, show a collapsible "Quality Gates" section:

```
▼ Simulation Quality Gates
  ✓ S1 Zero error rate    — 200/200 personas completed
  ✓ S2 Decision diversity — No option > 90% (max: Buy at 62%)
  ✓ S3 Driver coherence   — Top drivers are category-relevant
  ⚠ S4 WTP plausibility   — Median WTP ₹656 (ask: ₹649) — within ±30%

  BV3 Temporal consistency — PASS (avg confidence +14 across positive arc)
  BV6 Override scenarios   — PASS (1/2 personas departed from tendency)
```

**Implementation:** Goose wires `GateReport` objects from `simulation_gates.py` (Sprint 21) into the existing results display.

---

## Non-Breaking Changes (no user-visible change)

| Change | Why |
|---|---|
| Replace `src.taxonomy.schema.Persona` import with `PersonaRecord` from Simulatte | Old schema deprecated |
| Replace `JourneyConfig` → `run_loop` mapping with `simulatte_batch_runner.py` | Old batch runner removed |
| `@st.cache_data` on `load_simulatte_cohort()` | Prevents reloading 4.7MB file on every interaction |

---

## Changes NOT Required

- The journey preset definitions (`PRESET_JOURNEY_A/B/C`) — stimulus text is compatible with `run_loop`
- The Results tab export format — `simulatte_batch_runner.py` returns the same schema
- The "Ask the Population" page — uses narrative text which is unaffected by schema change
- The constraint violations report — not surfaced from new engine (legacy data)

---

## Implementation Sequence for Sprint 23

```
1. OpenCode → app_adapter.py (adapter layer) — must be done first
2. Codex → simulatte_batch_runner.py — depends on adapter
3. Antigravity → test_app_adapter.py — can parallelize with Codex
4. Goose → streamlit_app.py updates — depends on 1 and 2
5. OpenCode → 3 UI components — can parallelize with Goose
```
