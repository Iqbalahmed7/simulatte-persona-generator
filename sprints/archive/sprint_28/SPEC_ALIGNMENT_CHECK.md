# Sprint 28 — Master Spec Alignment Check
**Date:** 2026-04-03
**Sprint:** 28 — Domain Onboarding: Feature Construction + Cluster Derivation + Client Workflow
**Checked by:** Tech Lead

---

## Settled Decisions (§14A)

| Decision | Requirement | Status |
|---|---|---|
| O7: Cluster count K via BIC/AIC, min=3, max=8 | BIC sweep over k_range=(3,8); best_k = argmin(BIC) | ✅ PASS |
| O6: Minimum 200 signals | G-O1 enforces n_valid >= 200 | ✅ PASS |
| S1: LLM is cognitive engine | feature_builder, cluster_pipeline, onboarding_workflow: zero LLM calls | ✅ PASS |
| S18: Experiment isolation | Workflow is stateless; ClusterResult is pure output | ✅ PASS |

---

## Constitution Principles

| Principle | Check | Status |
|---|---|---|
| P2: LLM is cognitive engine | All feature and cluster computation deterministic | ✅ PASS |
| P8: Domain-agnostic core | onboarding pipeline operates independently of persona generation core | ✅ PASS |
| P10: Traceability | ClusterResult carries bic_scores, k_range_tried, silhouette_scores, notes; GateResult carries detail + action_required | ✅ PASS |

---

## Grounding Strategy (§7)

| Stage | Implementation | Status |
|---|---|---|
| Stage 2: Feature Construction | feature_builder.py: 5-category BehaviouralFeatures from TaggedCorpus | ✅ PASS |
| Stage 3: Cluster Derivation | cluster_pipeline.py: GMM BIC-optimal K; 5-run silhouette stability | ✅ PASS |
| Stage 4: Tendency Assignment | Deferred — workflow produces ClusterResult; tendency mapping is Sprint 29+ | DEFERRED |

---

## New Validity Gates

| Gate | Threshold | Implementation | Status |
|---|---|---|---|
| G-O1 | n_valid_signals ≥ 200 | check_go1() in onboarding_gates.py; registered in gate_report.py | ✅ PASS |
| G-O2 | silhouette > 0.30 across 5 runs | check_go2() in onboarding_gates.py; registered in gate_report.py | ✅ PASS |

---

## Directional Assessment

**Are we moving forward?** ✅ Yes.

Sprints 26–28 together complete the domain onboarding track:
- Sprint 26: Template library + auto-selection + collision detection
- Sprint 27: Signal ingestion + PII redaction + tagging
- Sprint 28: Feature construction + GMM clustering + 7-step workflow + gates

Sprint 29 (next): Multilingual validation framework (O15 BLOCKER active).

**No drift detected.**
