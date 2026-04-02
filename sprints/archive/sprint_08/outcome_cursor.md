# SPRINT 8 OUTCOME — CURSOR
**Engineer:** Cursor
**Role:** Signal Extractor + Signal-to-Vector Converter
**Sprint:** 8 — Grounding Pipeline
**Date:** 2026-04-02
**Status:** COMPLETE

---

## 1. Files Created

| File | Lines | Notes |
|------|-------|-------|
| `src/grounding/__init__.py` | 4 | Package init |
| `src/grounding/types.py` | 103 | STUB — created because OpenCode's full types.py did not yet exist; contains Signal, SignalType, and BehaviouralArchetype. Marked with `# STUB — will be replaced by OpenCode's full types.py`. |
| `src/grounding/signal_extractor.py` | 170 | Full implementation: extract_signals + signals_to_vectors |
| `tests/test_grounding_signal.py` | 87 | 10 tests, all passing |

**Total new lines:** 364

---

## 2. Keyword Taxonomy

Five keyword sets, all matched case-insensitively via `text.lower()`:

### PRICE_KEYWORDS
```
price, cost, expensive, cheap, affordable, discount, ₹, $, £, fee, charge, costly, budget, free
```

### PURCHASE_KEYWORDS
```
bought, purchased, chose, selected, tried, ordered, picked up, went with, decided to buy, got it
```

### REJECTION_KEYWORDS
```
refused, avoided, won't buy, not buying, returned, cancelled, rejected, passed on, skipped, didn't buy
```

### SWITCHING_KEYWORDS
```
switched, changed to, moved to, switched from, changed from, no longer using, replaced
```

### TRUST_KEYWORDS
```
recommended by, doctor, expert, review says, trusted, certified, dermatologist, nutritionist, my friend said, according to
```

All five sets are checked independently for every input text. A text can match multiple sets, producing one Signal per matched type. If no set matches, a single fallback `price_mention` Signal is emitted to guarantee at least 1 Signal per non-empty input.

---

## 3. signals_to_vectors — 9-Dimension Description

| Index | Name | Rule |
|-------|------|------|
| 0 | price_flag | 1.0 if `signal_type == "price_mention"`, else 0.0 |
| 1 | trust_expert | 1.0 if "expert", "doctor", or "certified" in text (case-insensitive) |
| 2 | trust_peer | 1.0 if "friend", "peer", or "recommended" in text |
| 3 | trust_brand | 1.0 if "brand" or "branded" in text |
| 4 | trust_community | 1.0 if "review", "community", or "users" in text |
| 5 | switching_price | 1.0 if `signal_type == "switching"` AND any PRICE_KEYWORD in text |
| 6 | switching_service | 1.0 if `signal_type == "switching"` AND ("service" or "quality") in text |
| 7 | trigger_need | 1.0 if "need", "required", or "essential" in text |
| 8 | trigger_rec | 1.0 if "recommended", "told me", or "suggested" in text |

All values are binary floats (0.0 or 1.0), so all values are in [0.0, 1.0]. No numpy or sklearn used — standard library only.

---

## 4. Test Results

```
tests/test_grounding_signal.py::test_price_mention_detected        PASSED
tests/test_grounding_signal.py::test_purchase_trigger_detected     PASSED
tests/test_grounding_signal.py::test_rejection_detected            PASSED
tests/test_grounding_signal.py::test_switching_detected            PASSED
tests/test_grounding_signal.py::test_trust_citation_detected       PASSED
tests/test_grounding_signal.py::test_multi_signal_text             PASSED
tests/test_grounding_signal.py::test_empty_text_skipped            PASSED
tests/test_grounding_signal.py::test_signals_to_vectors_shape      PASSED
tests/test_grounding_signal.py::test_signals_to_vectors_price_flag PASSED
tests/test_grounding_signal.py::test_fallback_signal_for_unmatched_text PASSED

10 passed in 0.03s
```

**Result: 10/10 PASS**

---

## 5. Known Gaps

1. **types.py is a stub.** The STUB `src/grounding/types.py` only defines `Signal`, `SignalType`, and a `BehaviouralArchetype` shell. OpenCode's full `types.py` includes `BehaviouralFeatures` (with `to_vector()`), `GroundingPipelineResult`, and other pipeline types. When OpenCode's full file lands, the stub must be replaced. The `Signal` and `SignalType` definitions are spec-compliant and should survive the replacement unchanged.

2. **Multi-phrase keyword matching is substring-based.** Multi-word keywords (e.g. "went with", "picked up", "my friend said") are matched by `in text_lower`, which means they match as substrings anywhere in the text. This is consistent with the brief's spec and acceptable for the MVP keyword-matching approach.

3. **No deduplication across signal types.** If a text matches both `PURCHASE_KEYWORDS` and `TRUST_KEYWORDS`, two separate Signal objects are emitted with the same `text` field. Downstream aggregation (Goose/Codex) must handle this correctly.

4. **Fallback always assigns `price_mention`.** Unclassified text falls back to `price_mention` rather than a dedicated `"unknown"` type. This matches the brief's spec but may inflate `price_salience_index` in BehaviouralFeatures if the corpus contains many vague texts.

5. **No platform/rating/date/category population.** `extract_signals` does not parse or infer metadata fields — they remain `None`. These must be populated by the upstream caller or a later enrichment step.
