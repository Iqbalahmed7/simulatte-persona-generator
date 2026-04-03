"""src/onboarding/feature_builder.py

Derives behavioural feature vectors from a tagged signal corpus.

No LLM calls — all features are computed deterministically from
TaggedCorpus.signals and TaggedCorpus.tag_distribution.

Spec ref: Sprint 28, Master Spec §7 (trigger verb taxonomy).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.onboarding.signal_tagger import TaggedCorpus

# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------


@dataclass
class BehaviouralFeatures:
    """5-category feature vector derived from a tagged signal corpus."""

    price_salience_index: float  # 0.0–1.0: fraction of signals mentioning price

    trust_source_distribution: dict[str, float]
    # {"doctor": 0.X, "friend": 0.X, "review": 0.X, "certification": 0.X, "other": 0.X}

    switching_trigger_distribution: dict[str, float]
    # {"price": 0.X, "quality": 0.X, "availability": 0.X, "recommendation": 0.X, "other": 0.X}

    objection_cluster_frequencies: dict[str, float]
    # {"price": 0.X, "trust": 0.X, "convenience": 0.X, "efficacy": 0.X, "other": 0.X}

    purchase_trigger_distribution: dict[str, float]
    # {"social": 0.X, "authority": 0.X, "promotional": 0.X, "habit": 0.X, "other": 0.X}

    n_signals: int           # total signals processed
    n_decision_signals: int  # non-neutral signals


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_TRUST_KEYWORDS: dict[str, list[str]] = {
    "doctor": ["doctor", "physician", "pediatrician", "specialist"],
    "friend": ["friend", "family", "relative", "neighbour", "neighbor"],
    "review": ["review", "rating", "testimonial", "feedback"],
    "certification": ["certif", "award", "standard", "approved"],
}

_SWITCHING_KEYWORDS: dict[str, list[str]] = {
    "price": ["price", "cost", "expensive", "cheap"],
    "quality": ["quality", "better", "superior", "inferior"],
    "availability": ["avail", "stock", "find", "shelf"],
    "recommendation": ["recommend", "suggest", "told", "advised"],
}

_OBJECTION_KEYWORDS: dict[str, list[str]] = {
    "price": ["price", "expensive", "cost", "afford"],
    "trust": ["trust", "unsure", "doubt", "credib"],
    "convenience": ["conven", "hard", "diffic", "effort"],
    "efficacy": ["work", "effect", "result", "proof"],
}

_PURCHASE_TRIGGER_KEYWORDS: dict[str, list[str]] = {
    "social": ["friend", "family", "recommend", "told"],
    "authority": ["doctor", "expert", "specialist", "research"],
    "promotional": ["discount", "offer", "sale", "promo", "deal"],
    "habit": ["always", "usual", "habit", "regular"],
}

# Zero-value dicts returned when there are no signals for a category
_EMPTY_TRUST = {"doctor": 0.0, "friend": 0.0, "review": 0.0, "certification": 0.0, "other": 0.0}
_EMPTY_SWITCHING = {"price": 0.0, "quality": 0.0, "availability": 0.0, "recommendation": 0.0, "other": 0.0}
_EMPTY_OBJECTION = {"price": 0.0, "trust": 0.0, "convenience": 0.0, "efficacy": 0.0, "other": 0.0}
_EMPTY_PURCHASE = {"social": 0.0, "authority": 0.0, "promotional": 0.0, "habit": 0.0, "other": 0.0}


def _keyword_fraction(
    signals: list[str],
    keyword_groups: dict[str, list[str]],
) -> dict[str, float]:
    """For each signal, assign to the first matching group. Compute fractions.

    A signal is matched to the first group (in insertion order) whose keyword
    list contains at least one substring match. Unmatched signals are counted
    under "other".
    """
    counts: dict[str, int] = {k: 0 for k in keyword_groups}
    counts["other"] = 0

    for text in signals:
        text_lower = text.lower()
        matched = False
        for group, keywords in keyword_groups.items():
            if any(kw in text_lower for kw in keywords):
                counts[group] += 1
                matched = True
                break
        if not matched:
            counts["other"] += 1

    total = max(sum(counts.values()), 1)
    return {k: v / total for k, v in counts.items()}


def _signals_for_tag(corpus: "TaggedCorpus", tag: str) -> list[str]:
    """Return the raw text of every signal with the given tag."""
    return [ts.text for ts in corpus.signals if ts.tag == tag]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_features_from_tagged_corpus(
    corpus: "TaggedCorpus",
    icp_spec: Any = None,
) -> BehaviouralFeatures:
    """Derive 5 behavioural feature categories from a TaggedCorpus.

    All computation is keyword-based within the tagged signal texts.
    icp_spec is accepted but not required (reserved for future
    domain-specific weighting).

    No LLM calls.

    Parameters
    ----------
    corpus:
        A TaggedCorpus produced by signal_tagger.tag_signals[_async].
    icp_spec:
        Optional ICPSpec instance.  Ignored in the current implementation;
        present for forward-compatibility with domain-specific weighting.

    Returns
    -------
    BehaviouralFeatures
        All float values are in [0.0, 1.0].  All distribution dicts sum to
        ~1.0 (within floating-point precision).  An empty corpus returns all
        zeros.
    """
    n_signals = len(corpus.signals)

    # ------------------------------------------------------------------
    # Empty-corpus fast path
    # ------------------------------------------------------------------
    if n_signals == 0:
        return BehaviouralFeatures(
            price_salience_index=0.0,
            trust_source_distribution=dict(_EMPTY_TRUST),
            switching_trigger_distribution=dict(_EMPTY_SWITCHING),
            objection_cluster_frequencies=dict(_EMPTY_OBJECTION),
            purchase_trigger_distribution=dict(_EMPTY_PURCHASE),
            n_signals=0,
            n_decision_signals=0,
        )

    # ------------------------------------------------------------------
    # 1. Price salience index
    # ------------------------------------------------------------------
    price_count = corpus.tag_distribution.get("price_mention", 0)
    price_salience_index = price_count / max(n_signals, 1)

    # ------------------------------------------------------------------
    # 2. Trust source distribution
    # ------------------------------------------------------------------
    trust_texts = _signals_for_tag(corpus, "trust_citation")
    if trust_texts:
        trust_source_distribution = _keyword_fraction(trust_texts, _TRUST_KEYWORDS)
    else:
        trust_source_distribution = dict(_EMPTY_TRUST)

    # ------------------------------------------------------------------
    # 3. Switching trigger distribution
    # ------------------------------------------------------------------
    switching_texts = _signals_for_tag(corpus, "switching")
    if switching_texts:
        switching_trigger_distribution = _keyword_fraction(switching_texts, _SWITCHING_KEYWORDS)
    else:
        switching_trigger_distribution = dict(_EMPTY_SWITCHING)

    # ------------------------------------------------------------------
    # 4. Objection cluster frequencies
    # ------------------------------------------------------------------
    rejection_texts = _signals_for_tag(corpus, "rejection")
    if rejection_texts:
        objection_cluster_frequencies = _keyword_fraction(rejection_texts, _OBJECTION_KEYWORDS)
    else:
        objection_cluster_frequencies = dict(_EMPTY_OBJECTION)

    # ------------------------------------------------------------------
    # 5. Purchase trigger distribution
    # ------------------------------------------------------------------
    purchase_texts = _signals_for_tag(corpus, "purchase_trigger")
    if purchase_texts:
        purchase_trigger_distribution = _keyword_fraction(purchase_texts, _PURCHASE_TRIGGER_KEYWORDS)
    else:
        purchase_trigger_distribution = dict(_EMPTY_PURCHASE)

    return BehaviouralFeatures(
        price_salience_index=price_salience_index,
        trust_source_distribution=trust_source_distribution,
        switching_trigger_distribution=switching_trigger_distribution,
        objection_cluster_frequencies=objection_cluster_frequencies,
        purchase_trigger_distribution=purchase_trigger_distribution,
        n_signals=n_signals,
        n_decision_signals=corpus.n_decision_signals,
    )
