# ICP Spec — Montage
*saas-video-production · Generated 2026-04-12*

---

## Section 1 — Business Problem

Montage is building a Watch & Decide navigator — a content producer layer for raw footage — targeting video professionals who lose significant project time deciding which clips to use. The research question is whether the problem (footage selection decision labor, derivative re-watch, absence of decision logging) is real and large enough to support a paid B2B SaaS tool, and which segments experience it most acutely.

**Simulation scope:** This simulation tests the Watch & Decide navigator concept (roadmap). The current Montage product (social clip repurposing tool, as of April 2026) is a separate artifact. Do not reference current product limitations in stimuli or corpus framing.

---

## Section 2 — Target Population

5 segments, each with a distinct relationship to the footage selection problem:

| ID | Label | Criteria Summary |
|---|---|---|
| S01 | The Craftsperson | Solo freelance videographer · weddings + corporate events · US/UK · 30–42 · $80K–$180K revenue |
| S02 | The Volume Handler | Event/conference videographer · multi-camera · US · 32–48 · $150K–$300K revenue |
| S03 | The Repetitive Processor | Podcast/webinar editor · freelance or network · US/UK · 25–38 · $40K–$120K |
| S04 | The Margin Manager | Small agency producer · 2–15 person agency · US · 30–45 · $200K–$2M agency revenue |
| S05 | The Lone Internal | In-house corporate video lead · marketing team · US · 27–40 · $60K–$110K salary |

---

## Section 3 — Persona Configuration

- **Number of personas:** 1 per slot (pilot cohort) — scale to n≥40 per slot before probe sessions
- **Pool type:** saas
- **Mode:** Simulation-Ready
- **Output:** JSON cohort + persona cards + cohort summary

---

## Section 4 — Anchor Traits (per slot)

Full anchor traits and anchor_overrides JSON documented in:
- `export/MASTER_INVOCATION_SPEC.md`
- `export/SLOT_SPECIFICATIONS.md`

Key anchors enforced in this generation run:
- autonomy_value gradient: S01(0.82) → S02(0.56) → S04(~0.52) → S05(0.38) → S03(0.34)
- All MISMATCH attributes overridden per attribute audit in SLOT_SPECIFICATIONS.md

---

## Section 5 — Domain Data

No external domain data provided for this run.

Partial validation signals embedded in ICP_DEFINITION.md FEEL Grounding Notes:
- S01 FEEL: Partially validated — Alina transcript Apr 2026: "Edit. Edit. It's our pain."
- S02 FEEL: Partially validated — Vladimir transcript Feb 2026 confirmed scale-driven volume pain

All other FEEL/SAY/ATTENTION signals are founder-authored grounding (F28⚑, F29⚑).

---

## Section 6 — Output Format

- Machine-readable: `cohort_montage_20260412.json`
- Human-readable: `persona_cards_montage_20260412.md`
- Cohort summary: `cohort_summary_montage_20260412.md`
- Save locations:
  - `Personas/generated/montage/`
  - `Persona Generator/pilots/montage/` (mirror)

---

## Authorised Source Documents

| Document | Role |
|---|---|
| `export/MASTER_INVOCATION_SPEC.md` | Per-slot criteria, anchor traits, decision bullets |
| `export/SLOT_SPECIFICATIONS.md` | Attribute audits, anchor_overrides JSON, corpus notes |
| `export/HYPOTHESIS_REGISTER.md` | 29 approved hypotheses with strongest challenges |
| `export/ICP_DEFINITION.md` | Archetype table, corrected coverage matrix |
| `coverage_matrix.md` | Full hypothesis × slot coverage with HIGH RISK flags |
| `stimuli.md` | 13 approved stimuli with sequencing constraints |

---

*ICP spec generated from morpheus Stage 3b approved artifacts. All stage gates passed: brief_approved=true · hypotheses_approved=true · persona_specs_approved=true · design_approved=true*
