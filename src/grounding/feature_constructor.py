"""Aggregate Signal list into BehaviouralFeatures.

Sprint 8 — Grounding Pipeline Stage 2.
No LLM calls. Pure rule-based aggregation.
"""
from __future__ import annotations

from src.grounding.types import Signal, BehaviouralFeatures

_ZERO_TRUST = {"expert": 0.0, "peer": 0.0, "brand": 0.0, "ad": 0.0, "community": 0.0}
_ZERO_SWITCH = {"price": 0.0, "feature": 0.0, "service": 0.0, "competitive": 0.0, "life_change": 0.0}
_ZERO_PURCHASE = {"need": 0.0, "recommendation": 0.0, "trial": 0.0, "promotion": 0.0, "event": 0.0}
_ZERO_OBJECTION = {"price": 0.0, "trust": 0.0, "information": 0.0}


def construct_features(signals: list[Signal]) -> BehaviouralFeatures:
    """Aggregate a list of Signals into BehaviouralFeatures.

    Args:
        signals: List of Signal objects (may be empty).

    Returns:
        BehaviouralFeatures with all proportions in [0.0, 1.0].
        If signals is empty, returns all-zero BehaviouralFeatures.
    """
    signal_count = len(signals)

    if signal_count == 0:
        return BehaviouralFeatures(
            price_salience_index=0.0,
            trust_source_distribution=dict(_ZERO_TRUST),
            switching_trigger_taxonomy=dict(_ZERO_SWITCH),
            purchase_trigger_taxonomy=dict(_ZERO_PURCHASE),
            objection_cluster_frequencies=dict(_ZERO_OBJECTION),
            signal_count=0,
        )

    # --- price_salience_index ---
    price_count = sum(1 for s in signals if s.signal_type == "price_mention")
    price_salience_index = price_count / signal_count

    # --- trust_source_distribution ---
    trust_signals = [s for s in signals if s.signal_type == "trust_citation"]
    trust_counts: dict[str, int] = {"expert": 0, "peer": 0, "brand": 0, "ad": 0, "community": 0}
    for s in trust_signals:
        txt = s.text.lower()
        if any(kw in txt for kw in ("expert", "doctor", "certified")):
            trust_counts["expert"] += 1
        elif any(kw in txt for kw in ("friend", "peer", "colleague")):
            trust_counts["peer"] += 1
        elif any(kw in txt for kw in ("brand", "branded")):
            trust_counts["brand"] += 1
        elif any(kw in txt for kw in ("review", "community", "users")):
            trust_counts["community"] += 1
        else:
            trust_counts["ad"] += 1

    n_trust = len(trust_signals)
    if n_trust == 0:
        trust_source_distribution = dict(_ZERO_TRUST)
    else:
        trust_source_distribution = {k: v / n_trust for k, v in trust_counts.items()}

    # --- switching_trigger_taxonomy ---
    switching_signals = [s for s in signals if s.signal_type == "switching"]
    switch_counts: dict[str, int] = {
        "price": 0, "feature": 0, "service": 0, "competitive": 0, "life_change": 0
    }
    for s in switching_signals:
        txt = s.text.lower()
        if any(kw in txt for kw in ("price", "cost", "expensive", "cheap")):
            switch_counts["price"] += 1
        elif any(kw in txt for kw in ("quality", "feature", "better")):
            switch_counts["feature"] += 1
        elif any(kw in txt for kw in ("service", "support", "delivery")):
            switch_counts["service"] += 1
        elif any(kw in txt for kw in ("competition", "competitor", "rival")):
            switch_counts["competitive"] += 1
        elif any(kw in txt for kw in ("moved", "life", "baby", "job", "home")):
            switch_counts["life_change"] += 1
        else:
            switch_counts["price"] += 1  # fallback

    n_switch = len(switching_signals)
    if n_switch == 0:
        switching_trigger_taxonomy = dict(_ZERO_SWITCH)
    else:
        switching_trigger_taxonomy = {k: v / n_switch for k, v in switch_counts.items()}

    # --- purchase_trigger_taxonomy ---
    purchase_signals = [s for s in signals if s.signal_type == "purchase_trigger"]
    purchase_counts: dict[str, int] = {
        "need": 0, "recommendation": 0, "trial": 0, "promotion": 0, "event": 0
    }
    for s in purchase_signals:
        txt = s.text.lower()
        if any(kw in txt for kw in ("need", "essential", "required", "must")):
            purchase_counts["need"] += 1
        elif any(kw in txt for kw in ("recommend", "told me", "suggested")):
            purchase_counts["recommendation"] += 1
        elif any(kw in txt for kw in ("trial", "tried", "sample", "free")):
            purchase_counts["trial"] += 1
        elif any(kw in txt for kw in ("sale", "discount", "promotion", "offer")):
            purchase_counts["promotion"] += 1
        elif any(kw in txt for kw in ("event", "occasion", "gift", "birthday")):
            purchase_counts["event"] += 1
        else:
            purchase_counts["need"] += 1  # fallback

    n_purchase = len(purchase_signals)
    if n_purchase == 0:
        purchase_trigger_taxonomy = dict(_ZERO_PURCHASE)
    else:
        purchase_trigger_taxonomy = {k: v / n_purchase for k, v in purchase_counts.items()}

    # --- objection_cluster_frequencies ---
    rejection_signals = [s for s in signals if s.signal_type == "rejection"]
    objection_counts: dict[str, int] = {"price": 0, "trust": 0, "information": 0}
    for s in rejection_signals:
        txt = s.text.lower()
        if any(kw in txt for kw in ("price", "cost", "expensive", "cheap")):
            objection_counts["price"] += 1
        elif any(kw in txt for kw in ("trust", "doubt")):
            objection_counts["trust"] += 1
        else:
            objection_counts["information"] += 1

    n_rejection = len(rejection_signals)
    if n_rejection == 0:
        objection_cluster_frequencies = dict(_ZERO_OBJECTION)
    else:
        objection_cluster_frequencies = {k: v / n_rejection for k, v in objection_counts.items()}

    return BehaviouralFeatures(
        price_salience_index=price_salience_index,
        trust_source_distribution=trust_source_distribution,
        switching_trigger_taxonomy=switching_trigger_taxonomy,
        purchase_trigger_taxonomy=purchase_trigger_taxonomy,
        objection_cluster_frequencies=objection_cluster_frequencies,
        signal_count=signal_count,
    )
