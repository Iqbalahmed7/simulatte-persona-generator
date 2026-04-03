# SPRINT 20 BRIEF — ANTIGRAVITY
**Role:** Tests
**Sprint:** 20 — MiroFish Domain Taxonomy Extraction
**Spec ref:** Validity Protocol (extraction quality), Master Spec §6
**Previous rating:** 20/20

---

## Context

You write the test suite for all four components delivered by Cursor, Codex, Goose, and OpenCode. Write tests against their interface specs — the implementations will be ready when you integrate.

**Do not call the live LLM in tests.** Mock `llm_client` using `unittest.mock.AsyncMock` where needed.

---

## File: `tests/test_domain_extractor.py`

### Test class: `TestExtractDomainAttributes`

```python
import pytest
from unittest.mock import AsyncMock, patch

# Synthetic corpus — 25 reviews about a child nutrition product
SYNTHETIC_CORPUS = [
    "Our pediatrician recommended Nutrimix and we immediately ordered it.",
    "I checked the ingredients carefully — no artificial colours, finally a clean product.",
    "My daughter refused to drink it after three days. Taste is really the dealbreaker.",
    # ... (write 22 more varied reviews covering doctor trust, clean label, price, taste)
]
```

| Test | What it checks |
|---|---|
| `test_empty_corpus_returns_empty` | `len(corpus) < 200` → returns `[]` and logs warning (no LLM call) |
| `test_icp_anchor_traits_set_source` | An extracted attribute matching an ICP anchor trait has `extraction_source == "icp_anchor"` |
| `test_corpus_attributes_set_source` | Attributes not in ICP anchors have `extraction_source == "corpus"` |
| `test_minimum_attributes_extracted` | With 200+ synthetic signals (patch `len` check), mock LLM returns 10 attrs; all 10 returned |
| `test_malformed_json_retry` | First LLM call returns invalid JSON, second returns valid → succeeds |
| `test_malformed_json_both_retries_fail` | Both calls return invalid JSON → returns partial result (empty list or whatever was parseable) |
| `test_no_demographic_attributes` | If LLM accidentally returns `{"name": "age", ...}` — it passes through (exclusion is the prompt's job, not the parser's) |

**Mock pattern:**
```python
mock_client = AsyncMock()
mock_client.messages.create = AsyncMock(return_value=MockResponse(
    content=[MockContent(text='[{"name": "pediatrician_trust", ...}]')]
))
```

---

## File: `tests/test_attribute_ranker.py`

### Test class: `TestRankAttributes`

Build a set of 10 `DomainAttribute` fixtures with varying signal_count, description language, and valid_range.

| Test | What it checks |
|---|---|
| `test_empty_input_returns_empty` | `rank_attributes([], ...) == []` |
| `test_low_signal_excluded` | Attribute with `signal_count=2` is excluded from output |
| `test_exact_base_name_excluded` | Attribute named `"brand_loyalty"` (in base taxonomy) excluded |
| `test_duplicate_near_name_excluded` | Attribute named `"brand_loyalty_score"` excluded by Jaccard |
| `test_continuous_scores_higher_than_categorical` | Attr with `"0.0-1.0"` range outscores attr with `"categorical: [a, b]"` when other factors equal |
| `test_decision_language_boosts_score` | Attr description containing "buy" and "trust" scores higher than one with neutral language |
| `test_top_n_respected` | `rank_attributes(..., top_n=3)` returns at most 3 results |
| `test_scores_descending` | Returned list is sorted descending by composite_score |

---

## File: `tests/test_domain_merger.py`

### Test class: `TestMergeTaxonomy`

| Test | What it checks |
|---|---|
| `test_base_not_mutated` | After `merge_taxonomy(base, attrs)`, original `base` dict is unchanged |
| `test_domain_specific_key_added` | Result contains `"domain_specific"` key |
| `test_base_keys_preserved` | All 6 base category keys still present in result |
| `test_layer_2_field_set` | Every entry in `domain_specific` has `"layer": 2` |
| `test_empty_attrs_gives_empty_domain` | `merge_taxonomy(base, [])` → `"domain_specific": {}` |
| `test_prior_domain_specific_replaced` | If base already has `"domain_specific"`, it is replaced by new merge |
| `test_conflict_detection` | `detect_conflicts(base, [attr_with_base_name])` returns that name |
| `test_get_domain_attribute_names` | Returns the correct set of keys from `domain_specific` |

---

## File: `tests/test_icp_spec_parser.py`

### Test class: `TestParseICPSpec`

Include the full markdown example from OpenCode's brief as a fixture string.

| Test | What it checks |
|---|---|
| `test_parse_json_dict` | Parses `{"domain": "cpg", "business_problem": "...", "target_segment": "..."}` correctly |
| `test_parse_json_synonyms` | Keys `"problem"`, `"segment"`, `"anchors"` parsed to correct ICPSpec fields |
| `test_parse_markdown` | Full markdown example → correct ICPSpec with all fields populated |
| `test_parse_markdown_anchor_traits` | Markdown anchor traits bullet list → `anchor_traits` list |
| `test_parse_markdown_missing_required_raises` | Markdown without `## Business Problem` → `ValueError` |
| `test_parse_json_string` | `parse_icp_spec('{"domain": "cpg", ...}')` works (string input) |
| `test_parse_path_json` | `parse_icp_spec(Path("fixture.json"))` works (write temp file in test) |
| `test_extra_fields_ignored` | JSON with unknown key `"foo"` does not raise |
| `test_empty_anchor_traits` | Markdown with no `## Anchor Traits` section → `anchor_traits == []` |

---

## Coverage target

≥ 30 tests total across all four files. All must pass. No live LLM calls.

---

## Outcome file

Write `sprints/outcome_antigravity.md`. List the test count per file and confirm 0 failures.
