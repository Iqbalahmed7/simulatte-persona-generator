# SPRINT 1 REVIEW
**Tech Lead: Claude**
**Date:** 2026-04-02
**Sprint:** Foundation — Schema + Taxonomy

---

## SPEC ALIGNMENT CHECK — Sprint 1 END

```
SPEC ALIGNMENT CHECK — Sprint 1 END
=============================================
Date: 2026-04-02

GOVERNING SECTIONS REVIEWED:
☑ §5 Persona Record Structure
☑ §6 Taxonomy Strategy (Layer 1 + Layer 2)
☑ §10 Constraint System
☑ §14A Settled Decisions

SETTLED DECISIONS CHECKED:
☑ No coefficient parameters introduced (S2, P4) — BehaviouralTendencies has bands + descriptions only
☑ Domain-agnostic core (S9, P8) — base_taxonomy.py has zero domain-specific attributes
☑ Tendencies carry source labels (S13, P10) — TendencyBand.source present on all tendency fields
☑ Every persona has ≥ 1 tension (S10, P9) — key_tensions validator enforces ≥ 1
☑ Memory not deferred (S3, P3) — full Memory schema implemented in Sprint 1

ANTI-PATTERNS CHECKED:
☑ No coefficient creep (A1) — behavioural_tendencies has no floats in the spec-violating sense
☑ Domain leakage into base taxonomy (A4) — zero domain attrs in base_taxonomy.py
☐ Validation theater (A5) — BV tests cannot yet run (Sprint 1 is schema + taxonomy only)

RESULT: [x] ALIGNED  [ ] DRIFT DETECTED
```

---

## Engineer Ratings

### CURSOR — Schema Architect
**Deliverables:** `src/schema/persona.py` (352 lines), `src/schema/cohort.py` (91 lines)

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Spec adherence | 5 | Exact match to spec. PriceSensitivityBand as a distinct model for "extreme" handling is the correct approach. `extra="forbid"` on all models prevents silent schema drift. |
| Output completeness | 5 | All sub-models present, all validators implemented, both files delivered, package `__init__.py` included. |
| Code quality | 5 | Clean, readable, fully typed. Continuous attribute range enforcement (0.0–1.0) as a model_validator is correct. Grounding distribution sum-to-1.0 enforcement is a good addition. |
| Acceptance criteria | 4 | G1 structural requirements all encodable. Minor gap: `persona_id` format check listed as partial (regex present but not enforced). `decision_style_score` and `consistency_score` range validators noted as missing in outcome file. |

**Overall: 19/20**

**Flag for Sprint 2:** Cursor should add range validators for `decision_style_score` (0.0–1.0) and `consistency_score` (0–100) in the next sprint or as a patch.

---

### CODEX — Taxonomy Architect
**Deliverables:** `src/taxonomy/base_taxonomy.py`

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Spec adherence | 5 | 150 attributes, 6 categories at exact target counts, 8 anchors in correct order. All 9 named-exact matches from `references/architecture.md` included. KNOWN_CORRELATIONS correctly defined as `list[tuple[str, str, str]]`. |
| Output completeness | 5 | All module-level exports present (BASE_TAXONOMY, ANCHOR_ATTRIBUTES, TAXONOMY_BY_CATEGORY, TAXONOMY_BY_NAME). Module-level assertion block validates structure on import — excellent. |
| Code quality | 5 | `_continuous()` and `_categorical()` factory helpers make definitions readable. Bidirectional correlation hints on per-attribute `positive_correlates`/`negative_correlates` are well-structured. |
| Acceptance criteria | 5 | All 6 categories, total 130–180, anchors in order, no domain-specific attrs. |

**Overall: 20/20**

---

### GOOSE — Generation Engine
**Deliverables:** `src/generation/attribute_filler.py` (247 lines)

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Spec adherence | 3 | Filling order logic present, LLM prompt matches spec, async batching implemented. However: 4 interface assumptions diverge from Codex's actual implementation (see breaking bugs below). |
| Output completeness | 4 | All required methods present: `fill()`, `_fill_single_attribute()`, `_get_fill_order()`, `_apply_correlation_check()`, async batching. |
| Code quality | 3 | `asyncio.run()` inside an async method is a known crash pattern. `hasattr` guards throughout suggest interface uncertainty rather than integration confirmation. Model name hardcoded to wrong version. |
| Acceptance criteria | 2 | Will not run as-is due to 4 breaking integration bugs with Codex's schema. |

**Overall: 12/20**

**Breaking bugs (must fix before Sprint 2):**

1. **`attr_def.type` → `attr_def.attr_type`** (lines 109, 112, 142, 148, 208). AttributeDefinition uses `attr_type` not `type`. Will throw `AttributeError` at runtime everywhere.

2. **KNOWN_CORRELATIONS format mismatch** (line 233). Goose calls `KNOWN_CORRELATIONS.get(newly_assigned, {})` treating it as a dict. Codex defined it as `list[tuple[str, str, str]]`. Will throw `AttributeError` at runtime. `_apply_correlation_check` needs full rewrite to iterate the list.

3. **`_is_domain` logic** (line 222). Checks `attr_def.is_domain_specific` which doesn't exist on `AttributeDefinition`. Domain attrs will never be identified and will be filed as extended attrs, violating Step 4 of the filling order. Fix: `AttributeFiller` should receive domain attrs separately (via `get_domain_attributes()` from template_loader) rather than trying to detect them on the definition object.

4. **`population_prior` type mismatch** (line 151). Fallback calls `attr_def.population_prior.get("value", 0.5)` as if it's a dict. Codex defines `population_prior: float | None`. Fix: `fallback_value = attr_def.population_prior if attr_def.population_prior is not None else 0.5`.

5. **`asyncio.run()` inside async method** (line 82). Raises `RuntimeError: This event loop is already running`. Fix: replace with `await asyncio.gather(*tasks)` directly, or restructure `_fill_batched` as an async method.

6. **Model name** (line 17). Brief specifies `"claude-sonnet-4-6"`, code has `"claude-3.5-sonnet"`.

7. **None-safety on `anchor_overrides`** (line 43). If `anchor_overrides=None` is passed, line 43 `for name, value in anchor_overrides.items()` will throw. Fix: guard with `if anchor_overrides:`.

---

### OPENCODE — Domain Template Architect
**Deliverables:** `cpg.py` (45 attrs), `saas.py` (40 attrs), `template_loader.py`

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Spec adherence | 4 | Good coverage across required areas, zero base taxonomy duplication, correct category assignments, no anchor attrs in domain templates. |
| Output completeness | 4 | All three files delivered with required interfaces. Missing: `src/taxonomy/domain_templates/__init__.py` — import will fail in some Python environments. |
| Code quality | 4 | template_loader.py is clean: duplicate detection, overlap check, normalised domain string handling, `__all__` export. Attribute definitions follow same pattern as base taxonomy. |
| Acceptance criteria | 4 | CPG 35–50 ✓, SaaS 35–50 ✓, zero base overlap ✓. Missing `__init__.py` is a gap. |

**Overall: 16/20**

**Minor fix needed:** Create `src/taxonomy/domain_templates/__init__.py` (can be empty).

---

### ANTIGRAVITY — Validator + Quality Enforcer
**Deliverables:** `src/schema/validators.py`, `src/generation/constraint_checker.py`, `src/generation/stratification.py`

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Spec adherence | 4 | All 6 HC checks and all 8 TR checks implemented. Stratification quantile-band logic is correct. ConstraintChecker correctly iterates KNOWN_CORRELATIONS as list of tuples (matches Codex). |
| Output completeness | 3 | Missing `sprints/outcome_antigravity.md`. All three code files delivered and functional. |
| Code quality | 4 | Solid and clean. KNOWN_CORRELATIONS tuple iteration is correct. `_get_attr_value` safe accessor duplicated between validators and constraint_checker — acceptable for now. `stratify()` edge case comment shows awareness of small-N rounding issue. |
| Acceptance criteria | 4 | HC1–HC6 all implemented, TR1–TR8 all implemented. Stratification produces correct 5:3:2 bands. |

**Overall: 15/20**

**Missing:** Outcome file `sprints/outcome_antigravity.md` — Antigravity must write this before Sprint 2.

---

## Sprint 1 Summary

| Engineer | Score | Status |
|----------|-------|--------|
| Cursor | 19/20 | Excellent. Minor validator gaps to patch. |
| Codex | 20/20 | Clean. No issues. |
| Goose | 12/20 | 7 bugs, 4 breaking. Must fix before Sprint 2 can integrate. |
| OpenCode | 16/20 | Missing `__init__.py`. Otherwise solid. |
| Antigravity | 15/20 | Missing outcome file. Code is good. |

**Sprint 1 gate status:**
- G1 (schema validity): ✓ Pydantic models pass
- G2 (hard constraints): ✓ HC1–HC6 implemented
- G3 (tendency-attribute): ✓ TR1–TR8 implemented
- Taxonomy (130–180 attrs, 6 categories): ✓ 150 attrs
- Anchor-first: ✓ 8 anchors in correct order
- Domain templates (30–60 per domain): ✓ CPG 45, SaaS 40

**Blocking for Sprint 2:** Goose's attribute_filler.py has 4 breaking integration bugs. These must be patched before Sprint 2 begins, as Sprint 2 (Identity Constructor) directly builds on the filler.

---

## Pre-Sprint 2 Patches Required

Before Sprint 2 briefs are issued, the following must be resolved:

1. Fix Goose's 7 bugs (items 1–7 above) — owner: Goose
2. Create `src/taxonomy/domain_templates/__init__.py` — owner: OpenCode
3. Write `sprints/outcome_antigravity.md` — owner: Antigravity
4. Optional patch: Cursor adds range validators for `decision_style_score` and `consistency_score`
