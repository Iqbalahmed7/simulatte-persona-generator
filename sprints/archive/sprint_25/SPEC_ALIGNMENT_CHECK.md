# Sprint 25 — Master Spec Alignment Check
**Date:** 2026-04-03
**Sprint:** 25 — Hierarchical Memory: Cross-Tier Retrieval + Extended Validation Gates
**Checked by:** Tech Lead

---

## Settled Decisions (§14A)

| Decision | Requirement | Status |
|---|---|---|
| S7: Retrieval formula | Tier decay applied as multiplier on composite score — not replacement | ✅ PASS |
| O3: Memory cap extension | Cross-tier retrieval activates only when archival_index is not None | ✅ PASS |
| S1: LLM is cognitive engine | No LLM calls in hierarchical_retrieval, rematerialisation, bv2/bv3_extended | ✅ PASS |
| S18: Experiment isolation | HierarchicalRetriever is stateless; no cross-persona state | ✅ PASS |

---

## Constitution Principles

| Principle | Check | Status |
|---|---|---|
| P2: LLM is cognitive engine | Retrieval is purely deterministic scoring; LLM not involved | ✅ PASS |
| P8: Domain-agnostic core | HierarchicalRetriever operates on memory structure only; no domain fields | ✅ PASS |
| P10: Traceability | Archived entries carry original_observation_ids; rematerialise() preserves tier and period | ✅ PASS |

---

## Acceptance Criteria

| Criterion | Result | Status |
|---|---|---|
| Decay: working_archive entry imp=9 (0.63×0.7=0.44) < active imp=7 (0.70×1.0=0.70) | Verified in tests | ✅ PASS |
| Budget: top-K=10, fraction=0.40 → max 4 archive entries | Verified in tests | ✅ PASS |
| Rematerialisation: all 6 keys present; ArchiveEntry not mutated | Verified in tests | ✅ PASS |
| Graceful degradation: identical output to WorkingMemoryManager on standard WorkingMemory | Verified — standard path unchanged | ✅ PASS |
| BV2 extended: 100% citation validity; ≥80% high-importance recall across tiers | Gate logic correct; verified in tests | ✅ PASS |
| BV3 extended: 100-turn arc; no >20-point drop at archival events | Gate logic correct; verified in tests | ✅ PASS |
| decide.py and reflect.py unchanged for standard WorkingMemory path | loop.py conditional: only triggers on WorkingMemoryExtended + archival_index | ✅ PASS |

---

## Deviation Logged

**loop.py modified (not decide.py/reflect.py)** — Sprint plan said to update decide.py and reflect.py but retrieve_top_k is called in loop.py. The change was made in the correct file. The intent (use HierarchicalRetriever when archival index present) is fully implemented.

---

## Directional Assessment

**Are we moving forward?** ✅ Yes.

Sprint 24 + Sprint 25 together complete the hierarchical memory capability. The archive write path (24) and read path (25) are both implemented and tested. Standard WorkingMemory paths are completely unaffected.

**No drift detected.**
