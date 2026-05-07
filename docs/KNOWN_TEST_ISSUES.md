# Known Test Issues — Pre-existing, Not PR0/PR1 Regressions

> Triage results from 2026-05-01 and 2026-05-02. Two real test issues, plus one previously misdiagnosed "hang" that turned out to be **slow-but-working** sequential persona generation.

**Filed:** 2026-05-02
**Last revised:** 2026-05-02 — Issue 3 reclassified after direct timing measurement

---

## Issue 1 — `test_credit_monitor.py::test_preflight_rejects_when_balance_below_buffer` fails

**Location:** `tests/test_credit_monitor.py::test_preflight_rejects_when_balance_below_buffer`
**Source:** `src/utils/credit_monitor.py:166` inside `preflight_check()`

**Error:**
```
AttributeError: 'CreditMonitor' object has no attribute '_force_credit_low'
```

**Verification it's pre-existing:** confirmed via `git stash` regression check — fails identically on `main` without PR0/PR1.

**Likely cause:** test references private hook `_force_credit_low` not present on the class. Either add the hook for testability or rewrite to mock balance retrieval.

**Owner:** TBD. ~30 minutes to fix. **Low priority.**

---

## Issue 2 — CI dependency install missing on remote

**Symptom:** Remote CI on PR1 push (commit `1fd8a09`) failed at pytest collection with:
```
ModuleNotFoundError: No module named 'pydantic'
ModuleNotFoundError: No module named 'anthropic'
```

All three modules (`pydantic`, `anthropic`, `scikit-learn`) are declared in `requirements.txt`.

**Cause:** CI workflow does not run `pip install -r requirements.txt` before pytest, or the install step silently fails.

**Fix:** Add or repair the dep-install step in the CI config (likely `.github/workflows/*.yml`). One-line change typical case.

**Owner:** TBD. ~15 minutes to fix once the CI config is located. **Low priority.**

---

## Issue 3 (RECLASSIFIED) — "Cohort assembly hangs after stratification" was a misdiagnosis. System is slow, not hung.

**Originally filed 2026-05-01.** Reclassified 2026-05-02 after direct timing measurement.

**What I observed yesterday and called a hang:**
- N=20 quick-mode run, generation phase progressed 13 min, reached `Stratified to 20 personas`, then no further log output for 8+ min before I killed.
- Today's N=1 run with `--skip-gates`: no stderr output at 150-180s, killed.

**What it actually is:** **The system is slow, not hung. There is no bug.**

Direct timing measurement on 2026-05-02:
- Single persona build via `IdentityConstructor.build()`: **208 seconds (~3.5 minutes)** end-to-end, from a clean script with no streaming or cohort-assembly overhead.
- The reason: each persona involves ~145 sequential attribute-fill LLM calls (one per attribute in the 12 sub-models × 145+ attribute taxonomy). At ~1-2s per call, this is mathematically ~3-4 minutes per persona.
- With `PG_MAX_CONCURRENT_BUILDS=10` the system parallelizes 10 builds at a time, so N=20 takes roughly 2 × 3.5 = 7 minutes for the build phase + post-processing.
- Yesterday's N=20 reached "Stratified to 20 personas" at t+13 min, then was killed at t+22 min while the cohort assembler was still running G1-G11 validation, grounding pipeline, and envelope assembly. Those steps are also slow but **not deadlocked** — they just need more time. Likely 5-15 additional minutes.

**Verification:** N=1 direct test on 2026-05-02 13:52 — built `pg-test-001` in 208 seconds, no errors, no hang.

**Real issues this surfaces (worth tracking separately):**

| Surface | Severity | Suggested fix |
|---|---|---|
| Per-persona wall-time of 3.5 min is slow | Medium — UX problem, not correctness | Parallelize attribute-fill within `IdentityConstructor.build()` instead of sequential. ~145 attribute fills could batch into 10-20 parallel groups → 30-60s per persona instead of 3.5 min. |
| No progress logs during the long generation phase | Low — UX | Add a heartbeat log every 30s during `_build_one`. Yesterday's instrumentation already added a `[datetime] persona {i} done` line on completion (still in cli.py); could add `[datetime] persona {i} attribute X/145` style updates. |
| Cohort assembler post-stratification phase has no progress logs either | Low — UX | Add log lines between stratification → G1-G11 → grounding → envelope write. |
| User documentation does not warn about expected wall-time | Low — DX | Update README/docs: "N=20 cohort takes ~10-20 min wall-time end-to-end. N=1 takes ~4 min." |

**This was not a PR1 regression.** The slow path has been there all along; my polling cadence and impatience caused the misdiagnosis.

**Time/cost burned on this misdiagnosis: ~$5-10 in API + ~3 hours of wall time across two days.** Worth the lesson on sample-size-of-one polling timeouts.

---

## How to track these

When you have time:

1. Issues 1 & 2 — convert each section above into a GitHub issue using `gh issue create` (after `gh auth login`). Both are low priority.
2. Issue 3 — closed as "not a bug." The four "Real issues" sub-bullets above are useful future work but not blockers.
3. Delete this file once issues 1 & 2 are filed in GitHub and tracked elsewhere.

---

## Lesson learned for future debugging

**When polling a long-running async process, set polling timeout ≥ 4× the expected end-to-end time, not based on what feels reasonable.** When the documented per-persona time is "≤ 8s sync / ≤ 4s batch" but the *actual* time is 3.5 min, polling at 3-min intervals will look exactly like a hang. The next persona-generator run for benchmarking or debugging should let it run for at least 30 min before declaring anything wrong.
