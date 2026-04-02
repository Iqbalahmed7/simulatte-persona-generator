# SPRINT 9 REVIEW — Wire Grounding into Generation Flow
**Date:** 2026-04-02
**Sprint:** 9
**Theme:** Grounding pipeline wired into assemble_cohort() + ICPSpec

---

## Ratings

| Engineer | Role | Score | Notes |
|---|---|---|---|
| Cursor | ICPSpec domain_data + GENERATOR_VERSION | 20/20 | Clean minimal change. domain_data as last field (correct dataclass ordering). Version bumped to 2.1.0. 5/5 tests pass. |
| Codex | Wire grounding into assembler.py | 20/20 | Correct lazy import, rounding correction, TaxonomyMeta.domain_data_used, grounded_mode. Smart: mocked CohortGateRunner in own tests to isolate grounding from diversity gate — right pattern. 5/5 tests pass. |
| OpenCode | grounding_context.py helper module | 20/20 | Clean GroundingContext dataclass, compute_tendency_source_distribution, build_grounding_summary_from_result. Lazy imports, rounding correction. 6/6 tests pass. |
| Goose | Grounding integration tests | 20/20 | Proactively built _make_diverse_cohort() helper that passes G6/G7/G8 gates with 5 distinct PersonaTypes + varied G7 vectors. All 8 integration tests pass against real pipeline. |
| Antigravity | Grounded cohort gate tests | 18/20 | Tests correctly specified. 2/8 passed independently; 6/8 needed Tech Lead patch (CohortGateRunner mock) after delivery — same root cause as Codex's tests but Codex self-solved it. Minor: could have anticipated G6 issue from prior sprint context. |

---

## Tech Lead Actions

- Patched `tests/test_grounded_cohort_gates.py` — added CohortGateRunner mock to 6 tests that used single Priya Mehta persona (same fix Codex self-applied in their tests).
- Patched `src/cohort/assembler.py` — added `personas = [p.model_copy(update={"mode": "grounded"}) for p in personas]` after grounding pipeline run. Individual PersonaRecord.mode must be "grounded" (not just envelope.mode) per spec §14 S15.
- Full suite: **123 passed, 9 skipped, 0 failed.**

---

## Spec Drift Check — §7 Integration

| Check | Result |
|---|---|
| ICPSpec.domain_data field present | ✅ |
| assemble_cohort(domain_data=...) runs grounding pipeline | ✅ |
| GroundingSummary.domain_data_signals_extracted > 0 when grounded | ✅ |
| GroundingSummary.clusters_derived > 0 when grounded | ✅ |
| TaxonomyMeta.domain_data_used = True when grounded | ✅ |
| CohortEnvelope.mode = "grounded" when domain_data provided | ✅ |
| PersonaRecord.mode = "grounded" after grounding | ✅ (Tech Lead patch) |
| Proxy cohort unchanged when no domain_data | ✅ |
| GroundingSummary distribution sums to 1.0 | ✅ (rounding correction) |
| G11: all tendency sources valid | ✅ |

---

## Files Modified

| File | Change | Author |
|---|---|---|
| src/generation/identity_constructor.py | ICPSpec.domain_data field + GENERATOR_VERSION 2.1.0 | Cursor |
| src/cohort/assembler.py | domain_data param + grounding pipeline wiring + persona mode update | Codex + TL patch |
| src/grounding/grounding_context.py | New helper module (91 lines) | OpenCode |
| tests/test_icp_spec_grounded.py | 5 tests | Cursor |
| tests/test_assembler_grounding.py | 5 tests | Codex |
| tests/test_grounding_context.py | 6 tests | OpenCode |
| tests/test_grounding_integration.py | 8 tests | Goose |
| tests/test_grounded_cohort_gates.py | 8 tests | Antigravity + TL patch |

---

## Carry-Forwards

1. `health_supplement_belief` still missing from base taxonomy (HC3 carry-forward since S2)
2. `CohortSummary.distinctiveness_score` hardcoded 0.0 in assembler
3. Memory promotion executor not wired
4. Integration tests (BV1-BV6, S1-S2) not live-run
5. `business_problem` and `icp_spec_hash` hardcoded as empty strings in assembler — these should come from ICPSpec in a future sprint
