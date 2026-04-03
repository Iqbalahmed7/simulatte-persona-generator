# SPRINT 20 BRIEF — CODEX
**Role:** Attribute Ranker
**Sprint:** 20 — MiroFish Domain Taxonomy Extraction
**Spec ref:** Master Spec §6 (Layer 2 domain extension), §7 (Grounded Mode — feature construction)
**Previous rating:** 19/20

---

## Context

Cursor's extractor may produce up to 80 candidate domain attributes from the corpus. Not all are equally useful. Your job is to rank them and select the top 30–60 for inclusion in the taxonomy. This is a **deterministic scoring step — no LLM calls**.

**Dependency:** You import `DomainAttribute` from `src.taxonomy.domain_extractor`. Write against the dataclass spec — it will be available when Cursor delivers.

---

## File: `src/taxonomy/attribute_ranker.py`

```python
"""src/taxonomy/attribute_ranker.py

Deterministic ranking and selection of extracted domain attributes.

Scores each DomainAttribute by:
  (a) decision_relevance   — does it directly affect buy/no-buy decisions?
  (b) discriminative_power — does it meaningfully differentiate personas?
  (c) data_coverage        — fraction of the corpus that mentions it
  (d) deduplication_penalty — penalise near-synonyms of base taxonomy attributes

No LLM calls. Deterministic only.

Spec ref: Master Spec §6 — domain extension should be scored and pruned, not verbatim.
"""
```

### Composite score

```
composite_score = (
    decision_relevance_score * 0.40
  + discriminative_score     * 0.35
  + coverage_score           * 0.25
  - dedup_penalty
)
```

- **`coverage_score`** = `min(attr.signal_count / total_signals, 1.0)`
- **`discriminative_score`** = `1.0` if `valid_range` contains `"0.0"` (continuous); `0.6` if `low|medium|high`; `0.4` for categorical with ≤ 3 options
- **`decision_relevance_score`** = text heuristic: count decision-language markers in `attr.description` (`buy`, `purchase`, `choose`, `avoid`, `switch`, `trust`, `prefer`, `recommend`, `decide`, `reject`). Score = `min(matches / 3, 1.0)` (caps at 3 matches → 1.0)
- **`dedup_penalty`** = `0.5` if `_is_duplicate(attr.name, base_names)` else `0.0`

### `_is_duplicate(attr_name: str, base_names: set[str]) -> bool`

Returns `True` if `attr_name` is a near-match to any base taxonomy attribute name. Near-match = either:
- Jaccard similarity of **character bigrams** > 0.6
- One is a substring of the other after stripping common suffixes (`_score`, `_level`, `_index`, `_bias`, `_orientation`)

If near-match: it's a duplicate — **exclude from ranking entirely** (not just penalise).

### Main function

```python
def rank_attributes(
    attributes: list["DomainAttribute"],
    base_taxonomy_names: set[str],
    total_signals: int,
    top_n: int = 50,
) -> list["DomainAttribute"]:
    """
    Score, sort, and select top_n domain attributes.

    Exclusion rules (applied before scoring):
    - signal_count < 3 → excluded (too rare)
    - exact name match with base taxonomy → excluded
    - _is_duplicate() → excluded

    Remaining: scored, sorted descending by composite_score, top_n returned.
    """
```

Each returned `DomainAttribute` should carry a `composite_score` float. If the dataclass is frozen, use a lightweight wrapper dataclass `RankedAttribute(attr: DomainAttribute, composite_score: float)`.

---

## What to build

1. `_bigram_set(text: str) -> set[str]` — helper for Jaccard
2. `_jaccard(a: set, b: set) -> float` — standard `|a ∩ b| / |a ∪ b|`
3. `_is_duplicate(attr_name, base_names)` — uses bigram Jaccard
4. `_score_one(attr, base_names, total_signals) -> float` — composite score
5. `rank_attributes(attributes, base_taxonomy_names, total_signals, top_n=50)` — main function

---

## Edge cases to handle

- Empty attribute list → return `[]`
- All attributes below signal threshold → return `[]`
- `total_signals = 0` → treat coverage as `0.0` (do not divide by zero)
- `top_n` greater than number of valid attributes → return all valid

---

## Outcome file

Write `sprints/outcome_codex.md`. Note any edge cases in the Jaccard logic, and confirm tests pass.
