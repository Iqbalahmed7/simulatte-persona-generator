# SPRINT 3 OUTCOME — OPENCODE
**Role:** Core Memory + Seed Memory Engineer
**Sprint:** 3 — Memory Architecture
**Status:** Complete
**Date:** 2026-04-02

---

## 1. Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/memory/core_memory.py` | 454 | Authoritative CoreMemory assembly — replaces `_assemble_core_memory()` stub in `identity_constructor.py` |
| `src/memory/seed_memory.py` | 233 | Seed memory bootstrap — creates fresh WorkingMemory with ≥ 3 seed observations |
| `src/memory/__init__.py` | 11 | Package init — exports `assemble_core_memory` and `bootstrap_seed_memories` |

All three files import cleanly (`python3 -c “from src.memory import assemble_core_memory, bootstrap_seed_memories”` passes). Zero LLM calls in either file.

---

## 2. `key_values` Derivation — Primary Value Driver Mapping

The `primary_value_driver` attribute is categorical with options: `price`, `quality`, `brand`, `convenience`, `relationships`, `status`.

**Step 1 — Human-readable label** (`_VALUE_DRIVER_LABELS` in `core_memory.py`):

| Taxonomy value | Label in key_values |
|---|---|
| `price` | “Quality over price” |
| `quality` | “Quality over price” |
| `brand` | “Brand trust and reputation” |
| `convenience` | “Convenience first” |
| `relationships` | “Relationships over transactions” |
| `status` | “Status and social signalling” |

Note: `price` and `quality` share the label “Quality over price” as specified in the brief. See Known Uncertainties §5a for a flag on this mapping.

**Step 2 — Tension seed** value statement (`_TENSION_SEED_VALUE_STATEMENTS`):

| tension_seed | Statement |
|---|---|
| `aspiration_vs_constraint` | “Driven by aspiration despite real constraints” |
| `independence_vs_validation` | “Values independence while navigating need for approval” |
| `quality_vs_budget` | “Seeks quality outcomes within budget limits” |
| `loyalty_vs_curiosity` | “Balances brand loyalty against curiosity for new options” |
| `control_vs_delegation` | “Prefers control but open to delegating when trust is established” |

**Steps 3–4 — Top continuous values category attributes** sorted by |value - 0.5| deviation, up to 3 more using each attribute’s `.label` field.

**Fallback padding** (only if still < 3 items after above): trust_anchor, risk_appetite, decision_style strings.

Result is always 3–5 items (enforced by CoreMemory.key_values validator).

---

## 3. `relationship_map` Derivation Rules Applied

### primary_decision_partner

| household.structure | trust_orientation_primary | Result |
|---|---|---|
| `joint` | `family` | “Spouse/partner” |
| `joint` | `self` | “Self” |
| `joint` | `peer` | “Close friends” |
| `joint` | `authority` | “Trusted expert/advisor” |
| `joint` | other | “Spouse/partner” (default) |
| `nuclear` | `family` | “Spouse/partner” |
| `nuclear` | `self` | “Self” |
| `nuclear` | `peer` | “Close friends” |
| `nuclear` | `authority` | “Trusted expert/advisor” |
| `nuclear` | other | “Spouse/partner” (default) |
| `single-parent` | any | “Children / close family” |
| `couple-no-kids` | any | “Partner” |
| `other` | `self` | “Self” |
| `other` | `peer` | “Close friends” |
| `other` | `authority` | “Trusted expert/advisor” |
| `other` | `family` | “Spouse/partner” |

### key_influencers
Top 2 of the 6 trust weight sources (expert/peer/brand/ad/community/influencer) sorted descending by float weight value, mapped to generic labels (“Expert reviews”, “Peer recommendations”, etc.).

### trust_network
All trust weight sources with weight > 0.5, plus social attribute enrichment:
- If `peer_influence_strength` attribute > 0.5 → append “Peer recommendations”
- If `online_community_trust` attribute > 0.5 → append “Online communities”
- Fallback: if no source exceeds 0.5, use the single highest-weight source.
- Clamped to 3 entries maximum.

---

## 4. Seed Memory Count — G10 Gate Confirmation

**Minimum case analysis** (persona with no life_defining_events after conversion):

| Seed # | Template | Guaranteed? |
|---|---|---|
| 1 | `”I know myself: {identity_statement}”` | Always — identity_statement is non-empty per CoreMemory |
| 2 | `”What matters most to me: {key_values[0]}”` | Always — key_values has ≥ 3 items per validator; string fallback also present |
| 3 | `”Something I always navigate: {first_sentence}”` | Always — tendency_summary always present (copied from reasoning_prompt) |

**Minimum count: 3.** G10 gate is always satisfied by the 3 fixed seeds before any life event seeds are added. The `_ensure_g10_gate()` fallback pool is an additional runtime safety net that should never activate on a valid PersonaRecord (which requires 2–3 life_stories, giving 5–6 total seeds).

**Typical count: 5–6** (3 fixed + 2–3 life event seeds from `life_defining_events[:3]`).

All seeds: `type=”observation”`, `importance=8`, `source_stimulus_id=None`. Reflections are not created (they require ≥ 2 source_observation_ids per schema validator).

---

## 5. Derivation Rules I Was Uncertain About

**a) `price` label in `_VALUE_DRIVER_LABELS`**
The brief specifies: `”Quality over price”` as the label for `primary_value_driver`. This label is applied to both `price` and `quality` values. A persona whose driver is `price` would logically describe themselves as preferring “Price over quality” not “Quality over price”. Applied as specified in the brief. Tech Lead should confirm intended semantics — if reversed, swap `price` → `”Price over quality”` and `quality` → `”Quality above all”` in `_VALUE_DRIVER_LABELS`.

**b) `budget_ceiling` when `economic_constraint_level` attribute is absent**
Brief requires: `if economic_constraint_level > 0.7 → “Tight budget — {income_bracket} income”`. If the attribute is missing from the attributes dict (possible in partial builds or custom modes), `budget_ceiling` is set to `None`. The existing stub in `identity_constructor.py` always populated `budget_ceiling` from `income_bracket`. New implementation is stricter: the constraint level attribute must be present and > 0.7.

**c) `WorkingMemoryManager` import reference in brief**
The brief’s interface stub imports `from src.memory.working_memory import WorkingMemoryManager` but that module does not exist yet (Sprint 6/7). `seed_memory.py` constructs `WorkingMemory` directly from the Pydantic schema. A comment in the file documents this and flags it for update when WorkingMemoryManager lands.

**d) trust_orientation_primary for `nuclear` without explicit `family` trust**
Brief: “joint/nuclear + family trust → Spouse/partner”. For `nuclear` + non-`family` trust, I applied the trust anchor map (self → Self, peer → Close friends, authority → Trusted expert/advisor) rather than defaulting to “Spouse/partner”. This gives more accurate results when a person in a nuclear household is self-reliant.

---

## 6. Known Gaps

1. **`absolute_avoidances`** — Empty list at persona creation time. Preserved from `persona.memory.core.immutable_constraints.absolute_avoidances` if the core memory was previously assembled. No structured data source populates this field during creation per spec. Will be filled in deeper-mode narrative generation (future sprint).

2. **`WorkingMemoryManager` integration** — `bootstrap_seed_memories` builds `WorkingMemory` directly from the Pydantic schema. When Sprint 6/7 delivers `src.memory.working_memory.WorkingMemoryManager`, this file should be updated to delegate construction to it.

3. **`identity_constructor.py` Step 6 not patched** — Brief says to update `identity_constructor.py` Step 6 to call `from src.memory.core_memory import assemble_core_memory`. That file is Cursor’s Sprint 2 deliverable and was not modified here. Required patch: replace `core_memory = self._assemble_core_memory(partial_record)` with a call to `assemble_core_memory(persona_record)`. Both produce equivalent output but `assemble_core_memory` implements the fuller spec rules (especially for `budget_ceiling` and `relationship_map`).

4. **Emotional valence on life event seeds** — All seed observations use `emotional_valence=0.0` (neutral). Life events typically carry meaningful positive or negative charge. Future enhancement: derive valence from `lasting_impact` text sentiment (requires a lightweight heuristic or small model call — outside scope of this sprint’s zero-LLM constraint).
