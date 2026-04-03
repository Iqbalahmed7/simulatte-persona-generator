# Sprint 20 — Master Spec Alignment Check
**Date:** 2026-04-03
**Sprint:** 20 — MiroFish Domain Taxonomy Extraction
**Checked by:** Tech Lead

---

## Settled Decisions (§14A)

| Decision | Requirement | Status |
|---|---|---|
| S1: LLM is cognitive engine | Extractor uses Sonnet for extraction — not for ranking/merging | ✅ PASS |
| S3: Core/working split | Sprint 20 touches taxonomy only — memory architecture untouched | ✅ PASS |
| S14: Narrative constrained by attributes | Not applicable this sprint | N/A |
| S17: Promotion rules | Not applicable this sprint | N/A |
| MiroFish adoption: scope limited to Layer 2 | Extractor outputs to `domain_specific` only; base taxonomy (Layer 1) never modified | ✅ PASS |
| MiroFish: ICP Spec + domain data trigger extraction | `ICPSpec` required; corpus < 200 falls back gracefully | ✅ PASS |
| MiroFish: zero-config rejected | `ICPSpec` is mandatory — user must define domain + business problem | ✅ PASS |

---

## Constitution Principles (P1–P10)

| Principle | Check | Status |
|---|---|---|
| P1: Persona is a synthetic person | Not applicable — taxonomy build sprint, no persona generation | N/A |
| P2: LLM is cognitive engine | Extractor uses Sonnet; ranker/merger are deterministic — correct split | ✅ PASS |
| P4: Tendencies are priors, not coefficients | No tendency logic in Sprint 20 | N/A |
| P8: Domain-agnostic core | `domain_specific` key is isolated; all 6 base categories verified untouched post-merge | ✅ PASS |
| P10: Traceability | `extraction_source` field on every `DomainAttribute`; `layer: 2` on every merged entry | ✅ PASS |

---

## Anti-Patterns (A1–A10)

| Anti-Pattern | Risk | Status |
|---|---|---|
| A1: Coefficients replacing reasoning | No decision functions introduced | ✅ PASS |
| A3: Domain leakage into base taxonomy | Verified via code check: `pediatrician_trust` not present in any base category after merge | ✅ PASS |
| A7: Static personas (no memory) | Not applicable this sprint | N/A |

---

## Phase Classification

Sprint 20 is correctly classified as **Phase 2 (Grounding)** per §14C. It does not:
- Jump ahead to Calibration (Phase 3)
- Build multi-agent social interaction (v2 roadmap)
- Add Zep Cloud or graph database (explicitly rejected)

---

## Validity Protocol Gates

| Gate | Applicability | Status |
|---|---|---|
| G1–G11 structural gates | Not triggered — no persona generation this sprint | N/A |
| BV1–BV6 behavioural tests | Not triggered — no simulation this sprint | N/A |
| S1–S4 simulation gates | Not triggered | N/A |
| C1–C5 calibration gates | Not triggered | N/A |
| Module 5 anti-stereotypicality | Not triggered | N/A |

---

## Directional Assessment

**Are we moving forward toward the spec's north star?**

✅ Yes. Sprint 20 fills the last in-scope v1 gap: automatic domain taxonomy extraction. The system can now move from "requires hand-authored templates for every new domain" to "reads domain data + ICP spec and derives the domain attribute set automatically." This directly enables true Grounded Mode for new clients.

**Any drift detected?**

None. The MiroFish principle is applied exactly as specified — LLM extraction for Layer 2 only, base taxonomy immutable, ICP Spec mandatory (not zero-config).

---

## Next Sprint Readiness

Sprint 21 (BV3/BV6 simulation quality gates) is unblocked. All Sprint 20 deliverables tested and merged.

**Remaining v1 gaps after Sprint 20:**
- BV3 temporal consistency test — automated and wired into pipeline (Sprint 21)
- BV6 override scenario test — automated (Sprint 21)
- Calibration engine (Sprint 22)
- LittleJoys app integration (Sprint 23)
