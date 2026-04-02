# SPRINT 8 BRIEF — CURSOR
**Role:** Signal Extractor + Signal-to-Vector Converter
**Sprint:** 8 — Grounding Pipeline
**Spec ref:** Master Spec §7 Stage 1 (Signal Extraction)
**Previous rating:** 20/20

---

## Context

Sprint 8 builds the Grounding Pipeline. Your job is Stage 1: parse raw text (reviews, posts) into typed `Signal` objects, and produce per-signal feature vectors for clustering.

The shared type `Signal` comes from `src/grounding/types.py` (written by OpenCode). You do not write types.py — import from it.

---

## Types contract (from `src/grounding/types.py`)

```python
from src.grounding.types import Signal, SignalType
# Signal fields: id, text, signal_type, platform, rating, date, category
# SignalType = Literal["purchase_trigger", "rejection", "switching", "trust_citation", "price_mention"]
```

---

## File 1: `src/grounding/signal_extractor.py`

### Detection rules (rule-based, no LLM)

Classify each text segment using keyword matching. A single text may emit **multiple** Signal objects if it contains multiple signal types. Minimum: 1 Signal per non-empty input text.

```python
PRICE_KEYWORDS     = {"price", "cost", "expensive", "cheap", "affordable", "discount",
                       "₹", "$", "£", "fee", "charge", "costly", "budget", "free"}

PURCHASE_KEYWORDS  = {"bought", "purchased", "chose", "selected", "tried", "ordered",
                       "picked up", "went with", "decided to buy", "got it"}

REJECTION_KEYWORDS = {"refused", "avoided", "won't buy", "not buying", "returned",
                       "cancelled", "rejected", "passed on", "skipped", "didn't buy"}

SWITCHING_KEYWORDS = {"switched", "changed to", "moved to", "switched from",
                       "changed from", "no longer using", "replaced"}

TRUST_KEYWORDS     = {"recommended by", "doctor", "expert", "review says",
                       "trusted", "certified", "dermatologist", "nutritionist",
                       "my friend said", "according to"}
```

### Interface

```python
import uuid
from src.grounding.types import Signal

def extract_signals(raw_texts: list[str]) -> list[Signal]:
    """Extract Signal objects from raw text strings.

    Each text may produce 1 or more signals (one per matching signal type).
    Texts with no keyword matches produce a single 'price_mention' signal
    as a fallback (to guarantee at least 1 signal per input).

    Args:
        raw_texts: List of raw text strings (reviews, posts, etc.)

    Returns:
        Flat list of Signal objects, one or more per input text.
    """
    ...


def signals_to_vectors(signals: list[Signal]) -> list[list[float]]:
    """Convert each Signal to a fixed 9-dim feature vector for clustering.

    Vector layout (must match BehaviouralFeatures.to_vector() order):
      0: price flag        — 1.0 if signal_type == "price_mention", else 0.0
      1: trust_expert      — 1.0 if "expert" or "doctor" or "certified" in text.lower(), else 0.0
      2: trust_peer        — 1.0 if "friend" or "peer" or "recommended" in text.lower(), else 0.0
      3: trust_brand       — 1.0 if "brand" or "branded" in text.lower(), else 0.0
      4: trust_community   — 1.0 if "review" or "community" or "users" in text.lower(), else 0.0
      5: switching_price   — 1.0 if signal_type == "switching" AND any price keyword in text, else 0.0
      6: switching_service — 1.0 if signal_type == "switching" AND ("service" or "quality") in text, else 0.0
      7: trigger_need      — 1.0 if "need" or "required" or "essential" in text.lower(), else 0.0
      8: trigger_rec       — 1.0 if "recommended" or "told me" or "suggested" in text.lower(), else 0.0

    Returns:
        List of 9-element float lists, one per signal. All values in [0.0, 1.0].
    """
    ...
```

### Implementation guidance

```python
def extract_signals(raw_texts: list[str]) -> list[Signal]:
    signals = []
    for text in raw_texts:
        if not text or not text.strip():
            continue
        text_lower = text.lower()
        found = False
        if any(kw in text_lower for kw in PRICE_KEYWORDS):
            signals.append(Signal(id=str(uuid.uuid4()), text=text, signal_type="price_mention"))
            found = True
        if any(kw in text_lower for kw in PURCHASE_KEYWORDS):
            signals.append(Signal(id=str(uuid.uuid4()), text=text, signal_type="purchase_trigger"))
            found = True
        if any(kw in text_lower for kw in REJECTION_KEYWORDS):
            signals.append(Signal(id=str(uuid.uuid4()), text=text, signal_type="rejection"))
            found = True
        if any(kw in text_lower for kw in SWITCHING_KEYWORDS):
            signals.append(Signal(id=str(uuid.uuid4()), text=text, signal_type="switching"))
            found = True
        if any(kw in text_lower for kw in TRUST_KEYWORDS):
            signals.append(Signal(id=str(uuid.uuid4()), text=text, signal_type="trust_citation"))
            found = True
        if not found:
            # Fallback: guarantee at least 1 signal per non-empty text
            signals.append(Signal(id=str(uuid.uuid4()), text=text, signal_type="price_mention"))
    return signals
```

---

## File 2: `tests/test_grounding_signal.py`

### Test 1: Price keyword detected

```python
def test_price_mention_detected():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["This product is too expensive for me."])
    types = [s.signal_type for s in signals]
    assert "price_mention" in types
```

### Test 2: Purchase keyword detected

```python
def test_purchase_trigger_detected():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["I bought this yesterday at the store."])
    types = [s.signal_type for s in signals]
    assert "purchase_trigger" in types
```

### Test 3: Rejection keyword detected

```python
def test_rejection_detected():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["I avoided buying this — too risky."])
    types = [s.signal_type for s in signals]
    assert "rejection" in types
```

### Test 4: Switching keyword detected

```python
def test_switching_detected():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["I switched from my old brand last month."])
    types = [s.signal_type for s in signals]
    assert "switching" in types
```

### Test 5: Trust citation detected

```python
def test_trust_citation_detected():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["My doctor recommended this supplement."])
    types = [s.signal_type for s in signals]
    assert "trust_citation" in types
```

### Test 6: Multi-signal text

```python
def test_multi_signal_text():
    """Text with price + trust triggers → at least 2 signals."""
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["It was expensive but my doctor recommended it."])
    assert len(signals) >= 2
```

### Test 7: Empty text skipped

```python
def test_empty_text_skipped():
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["", "  ", "I bought it."])
    assert len(signals) >= 1
    for s in signals:
        assert s.text.strip() != ""
```

### Test 8: signals_to_vectors shape

```python
def test_signals_to_vectors_shape():
    from src.grounding.signal_extractor import extract_signals, signals_to_vectors
    signals = extract_signals([
        "Too expensive — I avoided it.",
        "My friend recommended this brand.",
        "Switched to a cheaper option.",
    ])
    vectors = signals_to_vectors(signals)
    assert len(vectors) == len(signals)
    for v in vectors:
        assert len(v) == 9
        assert all(isinstance(x, float) for x in v)
        assert all(0.0 <= x <= 1.0 for x in v)
```

### Test 9: signals_to_vectors price flag

```python
def test_signals_to_vectors_price_flag():
    """price_mention signal → vector[0] == 1.0."""
    from src.grounding.signal_extractor import signals_to_vectors
    from src.grounding.types import Signal
    sig = Signal(id="test-1", text="Too expensive!", signal_type="price_mention")
    vector = signals_to_vectors([sig])[0]
    assert vector[0] == 1.0
```

### Test 10: Fallback signal for unmatched text

```python
def test_fallback_signal_for_unmatched_text():
    """Text with no keywords still produces 1 signal (fallback)."""
    from src.grounding.signal_extractor import extract_signals
    signals = extract_signals(["This is a vague comment with no specific words."])
    assert len(signals) >= 1
```

---

## Constraints

- No LLM calls. Pure keyword matching only.
- All signals have non-empty `id` (use `str(uuid.uuid4())`).
- `signals_to_vectors` returns exactly 9-element lists with floats in [0.0, 1.0].
- Empty or whitespace-only strings must be skipped.
- 10 tests, all pass without `--integration`.

---

## Outcome File

When done, write `sprints/outcome_cursor.md` with:
1. Files created (line counts)
2. Keyword taxonomy — all keyword sets used
3. signals_to_vectors — describe each dimension
4. Test results (pass/fail)
5. Known gaps
