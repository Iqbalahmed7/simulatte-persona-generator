# Sprint 27 Review — Domain Onboarding: Self-Service Data Ingestion + Signal Extraction

**Sprint lead:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** COMPLETE ✅

---

## Goal

Client-facing ingestion layer: CSV/JSON/plain-text upload, format inference, PII redaction, 200-signal minimum validation, and batch Haiku signal tagging. After this sprint, `simulatte onboard --data-file reviews.csv` works end-to-end.

## What Was Built

| Engineer | File | Rating |
|---|---|---|
| Cursor | `src/onboarding/__init__.py` — package marker | 20/20 |
| Cursor | `src/onboarding/format_inferrer.py` — DataFormat enum + infer_format() + parse_to_signals(); BOM-safe | 20/20 |
| Cursor | `src/onboarding/ingestion.py` — IngestionResult + ingest() orchestrator; lazy imports | 20/20 |
| Codex | `src/onboarding/pii_redactor.py` — RedactionLog + redact_pii(); email/phone/Aadhaar/honorific | 20/20 |
| Goose | `src/onboarding/signal_tagger.py` — TaggedSignal + TaggedCorpus + tag_signals(); Haiku; confidence<0.40→neutral | 20/20 |
| OpenCode | `src/onboarding/ingestion_validator.py` — ValidationReport + validate_corpus(); exact+near dedup; 200-signal threshold | 20/20 |
| Tech Lead | `src/cli.py` — added `onboard` CLI command | 20/20 |
| Antigravity | `tests/test_ingestion.py` — 30 tests, 0 bugs | 20/20 |

## Test Suite

- **783 tests passing, 0 failures** (up from 753)
- 30 new Sprint 27 tests

## Key Technical Findings

1. **Phone regex lookbehind fix** — Codex widened the lookbehind from `(?<!\d)` to `(?<![0-9A-Za-z])` so `+919876543210` is correctly captured (the `+` sign was blocking digit-only lookbehind on the `91` prefix).
2. **Near-dedup fixture design** — template signals like `"Consumer signal {i}"` have Jaccard > 0.85 due to shared long phrase. Antigravity used MD5-hashed tokens to generate genuinely distinct signals for boundary tests.
3. **Aadhaar vs phone disambiguation** — `+919876543210` is correctly tagged as phone (not Aadhaar) because the phone pattern fires first and the 12-digit Aadhaar pattern requires grouped-digit format.
4. **tag_distribution pre-seeded** — Goose pre-seeds all 6 tag keys at 0 so callers never encounter KeyError on sparse corpora.
5. **Lazy imports in ingestion.py** — all collaborator modules imported inside `ingest()` to prevent circular import failures during parallel development.

## Acceptance Criteria

- Format inference: all 4 formats + BOM-prefixed detected correctly ✅
- PII: email, Indian mobile, Aadhaar-pattern, Dr./Mr./Mrs./Ms. redacted; generic text untouched ✅
- Tagger: mock LLM tests pass; confidence<0.40 override verified ✅
- Validation: 200-signal threshold enforced; proxy_mode_suggested=True below threshold ✅
- CLI `simulatte onboard --data-file` works ✅
- No LLM calls in format_inferrer, ingestion_validator, ingestion orchestrator ✅
