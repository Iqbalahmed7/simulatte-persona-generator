# Sprint 21 — BV3 Temporal Consistency Test Runner: Outcome

## What was built

**File:** `src/validation/bv3_temporal.py`

Implements the BV3 temporal consistency test runner as specified in the Sprint 21 brief.

### Components

**`BV3Result` dataclass** — fields as specified:
- `passed: bool`, `persona_id: str`
- `check_a_passed: bool` — confidence trend across positive arc
- `check_b_passed: bool` — reflection references accumulation
- `check_c_passed: bool` — final decision cites both positive and mixed
- `confidence_sequence: list[int]` — confidence from each of 5 positive stimuli (only entries where `decision` was not None)
- `reflection_count: int`
- `failure_reasons: list[str]` — per-check failure messages
- `summary() -> str` — one-line human-readable result

**`run_bv3()` async function** — full arc logic:
1. Runs positive stimuli 1-5 through `run_loop` one at a time; appends `loop_result.decision.confidence` only when `decision is not None`.
2. After stimulus 5, snapshots `persona.memory.working.reflections` for Check B.
3. Runs mixed stimuli 6-9 through `run_loop` with no decision scenario.
4. Runs mixed stimulus 10 with `decision_scenario=_DECISION_SCENARIO`; captures `reasoning_trace` for Check C.
5. Evaluates checks A/B/C, aggregates failure reasons, builds and returns `BV3Result`.

**`run_bv3_sync()` wrapper** — uses `asyncio.run()` as specified.

**Stimulus arc:** 5 Littlejoys Nutrimix positive stimuli (pediatrician, friend, clean-label award, Subscribe & Save, school nutritionist) + 5 mixed stimuli (taste rejection, supplements-unnecessary post, neighbour stomach upset, price increase, diet-only article). Final scenario: "Should you buy Littlejoys Nutrimix for your child this month?"

### Check logic

| Check | Pass condition |
|-------|---------------|
| A — confidence trend | `seq[-1] >= seq[0]` AND `≤ 1` step drops > 15 points. Skip if < 2 values. |
| B — reflection trend reference | Any reflection after stimulus 5 contains one of: `pattern`, `noticing`, `trend`, `consistently`, `positive`, `accumul`, `building`, `trust` (case-insensitive). |
| C — final reasoning cites both arcs | Reasoning trace contains ≥ 1 positive keyword (`pediatrician`, `friend`, `award`, `subscribe`, `nutritionist`) AND ≥ 1 mixed keyword (`taste`, `refuses`, `unnecessary`, `price`, `stomach`, `diet`). |

## Deviations from brief

None. All stimuli, keyword sets, check thresholds, and interface signatures match the brief exactly.

## Edge cases handled

- **No decisions from positive stimuli:** confidence_sequence shorter than 5; Check A skips if < 2 entries.
- **Reflection accumulator never fires during positive arc:** Check B fails as expected — this is a genuine BV3 failure.
- **`run_loop` exception on any turn:** caught and logged as a warning; arc continues with partial data rather than aborting.
- **Missing `reasoning_trace` on final decision:** Check C returns False with an explicit failure reason.

## Verification

**Import check:**
```
python3 -c "from src.validation.bv3_temporal import BV3Result, run_bv3_sync; print('Import OK')"
Import OK
```

**Test suite:**
```
436 passed, 15 skipped in 2.02s
```

No regressions. All 436 existing tests pass. 15 skipped are integration/live tests unchanged from pre-sprint baseline.
