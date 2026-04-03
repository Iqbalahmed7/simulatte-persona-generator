# Sprint 29 Review — Multilingual Validation Framework

**Sprint lead:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** COMPLETE ✅

---

## Goal

Build the O15 multilingual validation framework. Language generation remains BLOCKED (O15 BLOCKER ACTIVE). What this sprint delivers: CR1-V through CR4-V gate definitions, LanguageReadinessReport aggregator, regional test harness, language-region compatibility matrix, and unlock governance protocol.

## What Was Built

| Engineer | File | Rating |
|---|---|---|
| Cursor | `src/validation/language_gates.py` — GateStatus, LanguageGateResult, CR1-V/CR2-V (NOT_RUN), CR3-V/CR4-V (evidence logic) | 20/20 |
| Cursor | `docs/MULTILINGUAL_UNLOCK_PROTOCOL.md` — 5-step unlock governance; O15 blocker rules | 20/20 |
| Codex | `src/validation/readiness_report.py` — ReadinessStatus; LanguageReadinessReport; build_readiness_report; tech_lead_sign_off_required=True always | 20/20 |
| Codex | `src/cli.py` — `language-readiness` CLI command added | 20/20 |
| Goose | `src/validation/regional_harness.py` — RegionalTestPersona; REGION_LANGUAGE_MAP (5 regions); generate_test_fixtures; check_language_region_validity | 20/20 |
| OpenCode | `src/validation/language_region_matrix.py` — LanguageRegionCompatibility; 24-entry matrix (16 compatible, 8 prohibited); alias resolution for ISO codes + full names | 20/20 |
| Antigravity | `tests/test_language_gates.py` — 55 tests, 0 failures | 20/20 |

## Test Suite

- **868 tests passing, 0 failures** (up from 813)
- 55 new Sprint 29 tests

## Key Technical Findings

1. **Codex/Cursor race on language_gates.py** — Codex wrote a stub (all four gates returning EVIDENCE_NEEDED) because Cursor hadn't written the file yet. Cursor subsequently wrote the full implementation, overwriting the stub. Final file is Cursor's. Public API surface was stable between stub and final, so readiness_report.py required no changes.
2. **ISO code alias resolution in language_region_matrix.py** — spec verification used full English names (`'hindi'`) but matrix stores ISO codes (`'hi'`). OpenCode added `_LANGUAGE_ALIASES` / `_REGION_ALIASES` dicts with `_normalise_language` / `_normalise_region` helpers so both `'hindi'` and `'hi'` resolve correctly. Also handles `'telangana'`, `'oriya'`, `'bengal'`, `'wb'`, `'up'` aliases.
3. **tech_lead_sign_off_required is constitutionally hardcoded True** — no code path can set it False. Enforced in readiness_report.py with an inline comment marking it an O15 constitutional requirement.
4. **O15_BLOCKER_REASON as module-level constant** — exported from language_gates.py so readiness_report.py and tests can import it directly without string duplication.
5. **Antigravity wrote 55 tests** — exceeded the 25-test target. Thorough matrix alias and prohibited-pairing coverage.

## Acceptance Criteria

- CR1-V, CR2-V: always NOT_RUN regardless of evidence ✅
- CR3-V: EVIDENCE_NEEDED → FAILED → READY state machine correct ✅
- CR4-V: pairs_tested<5 → EVIDENCE_NEEDED; pairs_confirmed<4 → FAILED; ≥4 → READY ✅
- build_readiness_report: BLOCKED/EVIDENCE_NEEDED/READY_FOR_REVIEW derived correctly ✅
- tech_lead_sign_off_required always True ✅
- regional_harness: 10 fixtures, correct compatible flags, zero-padded IDs ✅
- language_region_matrix: Hindi→Tamil Nadu prohibited; native pairings compatible ✅
- CLI `simulatte language-readiness --language hindi` returns JSON ✅
- O15 BLOCKER ACTIVE: no language generation code merged ✅
- All 55 tests pass ✅
