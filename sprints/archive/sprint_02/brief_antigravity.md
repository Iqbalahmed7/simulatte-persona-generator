# SPRINT 2 BRIEF — ANTIGRAVITY
**Role:** Validator — G4, G5 Gates
**Sprint:** 2 — Identity Constructor
**Spec check:** Master Spec §12 (Validity Protocol G4, G5), §14A S14 (narrative constrained by attributes)
**Previous rating:** 15/20 — Missing outcome file (patched). HC/TR spec alignment fixes applied. Good constraint logic.

---

## Your Job This Sprint

You own the two new validation gates for Sprint 2: G4 (narrative completeness) and G5 (narrative-attribute alignment). These run after identity construction is complete and check the quality of the generated narrative.

One file.

---

## File: `src/schema/validators.py` (extend existing file)

Add two new methods to the existing `PersonaValidator` class. Do not replace anything — append.

### G4 — Narrative Completeness

```python
def g4_narrative_completeness(self, persona: PersonaRecord) -> ValidationResult:
    """
    G4: 100% narrative completeness on sample personas.

    Checks:
    - narrative.first_person is non-empty and ≥ 50 words
    - narrative.third_person is non-empty and ≥ 80 words
    - narrative.display_name is non-empty
    - life_stories has 2–3 items (already checked in G1, recheck here for completeness)
    - Each life_story has non-empty title, when, event, lasting_impact
    - decision_bullets is non-empty (≥ 1 item)
    - memory.core.identity_statement is non-empty and ≥ 10 words
    - memory.core.tendency_summary is non-empty and ≥ 20 words
    """
    ...
```

### G5 — Narrative-Attribute Alignment

```python
def g5_narrative_attribute_alignment(self, persona: PersonaRecord) -> ValidationResult:
    """
    G5: 0 narrative-attribute contradictions on sample personas.

    Checks for detectable contradictions between narrative text and attribute values.
    Uses keyword scanning — not LLM-based (deterministic only).

    Rules to check:
    - If brand_loyalty > 0.80: narrative must NOT contain ["brand agnostic", "no brand preference",
      "doesn't care about brands", "any brand"]
    - If switching_propensity.band == "low": narrative must NOT contain ["loves trying new brands",
      "always exploring", "frequent switcher", "brand hopper"]
    - If price_sensitivity.band in ("high", "extreme"): narrative must NOT contain
      ["money is no object", "price doesn't matter", "never looks at price"]
    - If trust_orientation.dominant == "self": narrative must NOT contain
      ["follows the crowd", "does what others do", "easily influenced"]
    - If risk_appetite == "low": narrative must NOT contain
      ["thrill-seeker", "loves risk", "takes bold bets", "impulsive"]

    Check both first_person and third_person narrative.
    Case-insensitive matching.
    """
    ...
```

### Update `validate_all`

Update `validate_all` to optionally run G4 and G5:

```python
def validate_all(
    self,
    persona: PersonaRecord,
    include_narrative: bool = False,
) -> list[ValidationResult]:
    """
    Run G1, G2, G3 always.
    G4, G5 only when include_narrative=True (requires narrative to be generated).
    """
    results = [
        self.g1_schema_validity(persona),
        self.g2_hard_constraints(persona),
        self.g3_tendency_attribute_consistency(persona),
    ]
    if include_narrative:
        results.append(self.g4_narrative_completeness(persona))
        results.append(self.g5_narrative_attribute_alignment(persona))
    return results
```

---

## Integration Contract

- **Called by Cursor:** `PersonaValidator.validate_all(persona, include_narrative=True)` at Step 7 of identity build
- **No new imports needed** — all checks use schema fields already accessible

---

## Constraints

- G5 is **keyword-scan only** — no LLM calls. This is a deterministic gate.
- The keyword lists are a minimum set. You may expand them if you identify obvious contradiction signals, but do not add rules for conditions that require interpretation.
- G4 word count checks use simple `len(text.split())` — no NLP library required.

---

## Outcome File

When done, write `sprints/outcome_antigravity.md` (overwrite Sprint 1 patch version) with:
1. Methods added (confirm G4 and G5 present in validators.py)
2. G4 word count thresholds — justify why 50/80 words (or adjust with rationale)
3. G5 keyword lists — full list used for each contradiction check
4. `validate_all` signature change — confirm backward compatibility (include_narrative defaults False)
5. Known gaps: contradiction patterns you could not detect with keyword scanning
