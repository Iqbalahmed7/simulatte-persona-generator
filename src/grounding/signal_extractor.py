"""Signal extractor for the Grounding Pipeline.

Stage 1: parse raw text (reviews, posts) into typed Signal objects,
and produce per-signal feature vectors for clustering.

Sprint 8 — Grounding Pipeline.
No LLM calls. Pure keyword matching only.
"""
from __future__ import annotations

import uuid

from src.grounding.types import Signal

# ---------------------------------------------------------------------------
# Keyword taxonomy
# ---------------------------------------------------------------------------

PRICE_KEYWORDS = {
    "price", "cost", "expensive", "cheap", "affordable", "discount",
    "₹", "$", "£", "fee", "charge", "costly", "budget", "free",
}

PURCHASE_KEYWORDS = {
    "bought", "purchased", "chose", "selected", "tried", "ordered",
    "picked up", "went with", "decided to buy", "got it",
}

REJECTION_KEYWORDS = {
    "refused", "avoided", "won't buy", "not buying", "returned",
    "cancelled", "rejected", "passed on", "skipped", "didn't buy",
}

SWITCHING_KEYWORDS = {
    "switched", "changed to", "moved to", "switched from",
    "changed from", "no longer using", "replaced",
}

TRUST_KEYWORDS = {
    "recommended by", "doctor", "expert", "review says",
    "trusted", "certified", "dermatologist", "nutritionist",
    "my friend said", "according to",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_signals(raw_texts: list[str]) -> list[Signal]:
    """Extract Signal objects from raw text strings.

    Each text may produce 0 or more signals (one per matching signal type).
    Texts with no keyword matches produce no signals.

    Args:
        raw_texts: List of raw text strings (reviews, posts, etc.)

    Returns:
        Flat list of Signal objects, one or more per input text.
    """
    signals: list[Signal] = []

    for text in raw_texts:
        if not text or not text.strip():
            continue

        text_lower = text.lower()
        if any(kw in text_lower for kw in PRICE_KEYWORDS):
            signals.append(Signal(id=str(uuid.uuid4()), text=text, signal_type="price_mention"))

        if any(kw in text_lower for kw in PURCHASE_KEYWORDS):
            signals.append(Signal(id=str(uuid.uuid4()), text=text, signal_type="purchase_trigger"))

        if any(kw in text_lower for kw in REJECTION_KEYWORDS):
            signals.append(Signal(id=str(uuid.uuid4()), text=text, signal_type="rejection"))

        if any(kw in text_lower for kw in SWITCHING_KEYWORDS):
            signals.append(Signal(id=str(uuid.uuid4()), text=text, signal_type="switching"))

        if any(kw in text_lower for kw in TRUST_KEYWORDS):
            signals.append(Signal(id=str(uuid.uuid4()), text=text, signal_type="trust_citation"))

    return signals


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
    vectors: list[list[float]] = []

    for sig in signals:
        t = sig.text.lower()

        # dim 0: price flag
        price_flag = 1.0 if sig.signal_type == "price_mention" else 0.0

        # dim 1: trust_expert
        trust_expert = 1.0 if ("expert" in t or "doctor" in t or "certified" in t) else 0.0

        # dim 2: trust_peer
        trust_peer = 1.0 if ("friend" in t or "peer" in t or "recommended" in t) else 0.0

        # dim 3: trust_brand
        trust_brand = 1.0 if ("brand" in t or "branded" in t) else 0.0

        # dim 4: trust_community
        trust_community = 1.0 if ("review" in t or "community" in t or "users" in t) else 0.0

        # dim 5: switching_price
        switching_price = (
            1.0
            if sig.signal_type == "switching" and any(kw in t for kw in PRICE_KEYWORDS)
            else 0.0
        )

        # dim 6: switching_service
        switching_service = (
            1.0
            if sig.signal_type == "switching" and ("service" in t or "quality" in t)
            else 0.0
        )

        # dim 7: trigger_need
        trigger_need = 1.0 if ("need" in t or "required" in t or "essential" in t) else 0.0

        # dim 8: trigger_rec
        trigger_rec = (
            1.0 if ("recommended" in t or "told me" in t or "suggested" in t) else 0.0
        )

        vectors.append([
            price_flag,
            trust_expert,
            trust_peer,
            trust_brand,
            trust_community,
            switching_price,
            switching_service,
            trigger_need,
            trigger_rec,
        ])

    return vectors
