# Cohort Summary — Montage
*5 personas · saas-video-production · 2026-04-12*

---

## Distribution Stats

**Decision style distribution:**
| Style | Count | % |
|---|---|---|
| Emotional | 1 (pg-mvp-001 / Ryan) | 20% |
| Analytical | 2 (pg-mvp-002 / Marcus, pg-mvp-004 / Dana) | 40% |
| Habitual | 1 (pg-mvp-003 / Priya) | 20% |
| Social | 1 (pg-mvp-005 / Jordan) | 20% |

All four decision styles represented. ✓

**Trust anchor distribution:**
| Anchor | Count | % |
|---|---|---|
| Self | 2 (Marcus, Priya) | 40% |
| Peer | 2 (Ryan, Jordan) | 40% |
| Authority | 1 (Dana) | 20% |
| Family | 0 | 0% |

**Risk appetite distribution:**
| Appetite | Count | % |
|---|---|---|
| Low | 2 (Ryan, Dana) | 40% |
| Medium | 2 (Marcus, Priya) | 40% |
| High | 1 (Marcus at edge) | ~20% |

**Primary value orientation:**
| Orientation | Persona |
|---|---|
| Quality | Ryan (S01), Dana (S04) |
| Features | Marcus (S02) |
| Convenience | Priya (S03), Jordan (S05) |

**Consistency scores:** Mean 97 · Min 95 (Priya) · Max 99 (Marcus)

All personas pass the ≥60 consistency floor with substantial margin. ✓

---

## Cross-Slot Autonomy Gradient

This is the backbone of H08/H09. Spread is wide and well-distributed.

| Slot | Persona | autonomy_value | Expected H08 Position |
|---|---|---|---|
| S01 | Ryan Kowalski | 0.82 | Strong control preference — deal-breaker on AI selection |
| S02 | Marcus Webb | 0.56 | Moderate — open to AI-first on high-volume impersonal footage |
| S04 | Dana Chen | ~0.52 | Moderate — business-case driven; team adoption requirement |
| S05 | Jordan Tate | 0.38 | Low — actively wants help, not control |
| S03 | Priya Sundaram | 0.34 | Low — automation-open anchor; least control-attached of all five |

Gradient spread: 0.82 → 0.34 (range: 0.48). Sufficient for visible gradient effect in probe sessions. ✓

---

## Pain Profile by Slot

Each slot has a distinct primary pain signal. Single positioning cannot address all five:

| Slot | Primary Pain | Pain Frame | SAY Dismissal |
|---|---|---|---|
| S01 — Ryan | Post-shoot dread, lost creative momentum | Emotional / craft | "I already have Premiere" |
| S02 — Marcus | Re-watch cost across 96hrs of sponsor deliverables | Operational cost | "More deliverables = more revenue" |
| S03 — Priya | Accumulated invisible loss across 200+ episodes | Invisible until retrospective | "Descript is fine" |
| S04 — Dana | $3-5K/month unbilled derivative margin erosion | Financial / margin | "We have our process / Frame.io" |
| S05 — Jordan | Brief-gap anxiety — no structure before review starts | Competence / status | "We outsource complex stuff / CapCut is fine" |

---

## Persona Type Taxonomy

| Slot | Persona | Type |
|---|---|---|
| S01 | Ryan | Anxious Optimizer |
| S02 | Marcus | Power User |
| S03 | Priya | Reluctant User |
| S04 | Dana | Loyalist |
| S05 | Jordan | Pragmatist |

5 distinct types across 5 personas. ✓

---

## Notable Attribute Clusters

**Budget sensitivity split:** S03 (Priya, budget_consciousness 0.64) and S05 (Jordan, 0.72) are the price-sensitive anchors — any pricing above $20-30/month creates significant conversion friction for these segments. S02 (Marcus, 0.28) and S01 (Ryan, 0.44) are substantially less price-sensitive when ROI is demonstrated.

**Adoption friction cluster:** Three personas have high trial_before_commitment or free_trial_dependency (Ryan 0.75, Priya 0.80, Jordan 0.74) — the majority of the cohort will not convert without a trial. This has direct GTM implications for pricing model design.

**Team vs. solo adoption:** Four of five personas (S01, S02, S03, S05) make purchase decisions unilaterally. S04 (Dana) requires team adoption for value — this is the structural differentiator for the agency segment and explains her longer shortlisting timeline.

---

## Coverage Assessment

This cohort covers all 5 target slots (S01–S05) and spans all 4 decision styles. The autonomy gradient is preserved correctly from the SLOT_SPECIFICATIONS anchor_overrides. The primary coverage gap is **depth per slot**: this is a pilot cohort of 1 persona per slot.

For HIGH RISK hypotheses (H15, H17, H18, H23–H29) — each covered by a single archetype — the probe sessions require n≥40 per slot before statistically meaningful signal emerges. Additional generation runs needed.

**Recommended next step:** Scale each slot to n≥40 before running morpheus probe sessions. Priority order by hypothesis risk:
1. S01 (H23, H28 — HIGH RISK)
2. S02 (H15, H26 — HIGH RISK)
3. S03 (H18, H24 — HIGH RISK)
4. S04 (H17, H25, H29 — HIGH RISK)
5. S05 (H27 — HIGH RISK)

---

## Dominant Cohort Tensions

1. **Control vs. automation (H08/H09):** The gradient from Ryan (0.82) to Priya (0.34) is the widest differentiating axis in the cohort. If simulation collapses this gradient — producing similar automation responses across all five — investigate corpus contamination: the narrative framing may be overriding the attribute float.

2. **Pain framing incompatibility:** Ryan responds to creative energy recovery; Marcus to time-per-event ROI; Priya to cumulative repetition cost; Dana to specific margin loss amounts; Jordan to brief-gap competence. A single Montage ATTENTION message cannot speak to all five — the SAY/FEEL/ATTENTION hypotheses (H23–H27) are testing for exactly this fragmentation.

---

*Generated by persona-generator skill v1.0. Hard rule in force: no handcrafted personas. All personas produced through skill pipeline only.*
*Output files: cohort_montage_20260412.json · persona_cards_montage_20260412.md · cohort_summary_montage_20260412.md*
