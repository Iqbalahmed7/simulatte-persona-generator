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

from __future__ import annotations

import re
from dataclasses import dataclass

from src.taxonomy.domain_extractor import DomainAttribute

# ---------------------------------------------------------------------------
# Decision-relevance keyword list
# ---------------------------------------------------------------------------

_DECISION_KEYWORDS = {
    "buy",
    "purchase",
    "choose",
    "avoid",
    "switch",
    "trust",
    "prefer",
    "recommend",
    "decide",
    "reject",
}

# Suffixes to strip before near-duplicate comparison
_STRIP_SUFFIXES = (
    "_score",
    "_level",
    "_index",
    "_bias",
    "_orientation",
)


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------


@dataclass
class RankedAttribute:
    attr: DomainAttribute
    composite_score: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bigram_set(text: str) -> set[str]:
    """Return all character bigrams from *text* (lowercased, stripped)."""
    t = text.lower().strip()
    if len(t) < 2:
        return set()
    return {t[i : i + 2] for i in range(len(t) - 1)}


def _jaccard(a: set, b: set) -> float:
    """Standard Jaccard similarity: |a ∩ b| / |a ∪ b|. Returns 0.0 if union is empty."""
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _strip_suffixes(name: str) -> str:
    """Strip common attribute suffixes from *name* (applied once, longest-first)."""
    # Sort by length descending so we strip the longest matching suffix first
    for suffix in sorted(_STRIP_SUFFIXES, key=len, reverse=True):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _is_duplicate(attr_name: str, base_names: set[str]) -> bool:
    """Return True if *attr_name* is a near-match to any name in *base_names*.

    Near-match is defined as either:
    - Jaccard similarity of character bigrams > 0.6 (after stripping suffixes), OR
    - One stripped name is a substring of the other stripped name.
    """
    stripped_attr = _strip_suffixes(attr_name)
    bigrams_attr = _bigram_set(stripped_attr)

    for base_name in base_names:
        stripped_base = _strip_suffixes(base_name)

        # Substring check (both directions)
        if stripped_attr in stripped_base or stripped_base in stripped_attr:
            return True

        # Bigram Jaccard check
        bigrams_base = _bigram_set(stripped_base)
        if _jaccard(bigrams_attr, bigrams_base) > 0.6:
            return True

    return False


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _coverage_score(attr: DomainAttribute, total_signals: int) -> float:
    """Fraction of corpus signals that mention this attribute, capped at 1.0."""
    if total_signals == 0:
        return 0.0
    return min(attr.signal_count / total_signals, 1.0)


def _discriminative_score(attr: DomainAttribute) -> float:
    """Score based on the granularity of the attribute's valid range."""
    vr = attr.valid_range
    if "0.0" in vr:
        return 1.0
    if "low|medium|high" in vr:
        return 0.6
    return 0.4


def _decision_relevance_score(attr: DomainAttribute) -> float:
    """Count decision-language keywords in the description; cap at 3 → 1.0."""
    description_lower = attr.description.lower()
    # Split into words to avoid partial matches (e.g. "avoidance" counting as "avoid")
    words = re.findall(r"[a-z]+", description_lower)
    count = sum(1 for w in words if w in _DECISION_KEYWORDS)
    return min(count / 3, 1.0)


def _score_one(
    attr: DomainAttribute,
    base_names: set[str],
    total_signals: int,
) -> float:
    """Compute the composite score for a single attribute."""
    coverage = _coverage_score(attr, total_signals)
    discriminative = _discriminative_score(attr)
    decision_relevance = _decision_relevance_score(attr)
    dedup_penalty = 0.5 if _is_duplicate(attr.name, base_names) else 0.0

    return (
        decision_relevance * 0.40
        + discriminative * 0.35
        + coverage * 0.25
        - dedup_penalty
    )


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------


def rank_attributes(
    attributes: list[DomainAttribute],
    base_taxonomy_names: set[str],
    total_signals: int,
    top_n: int = 50,
) -> list[RankedAttribute]:
    """Score, sort, and select the top *top_n* domain attributes.

    Exclusion rules (applied before scoring):
    - signal_count < 3  → excluded (too rare)
    - exact name match with base taxonomy → excluded
    - _is_duplicate() → excluded (near-synonym of a base attribute)

    Remaining attributes are scored, sorted descending by composite_score,
    and the top *top_n* are returned as RankedAttribute objects.

    Args:
        attributes: Candidate DomainAttribute objects from the extractor.
        base_taxonomy_names: Names already in the base taxonomy (exact strings).
        total_signals: Total number of signals in the corpus (for coverage normalisation).
        top_n: Maximum number of attributes to return.

    Returns:
        List of RankedAttribute, sorted descending by composite_score.
    """
    if not attributes:
        return []

    ranked: list[RankedAttribute] = []

    for attr in attributes:
        # --- Exclusion: too rare ---
        if attr.signal_count < 3:
            continue

        # --- Exclusion: exact name match in base taxonomy ---
        if attr.name in base_taxonomy_names:
            continue

        # --- Exclusion: near-duplicate of a base taxonomy attribute ---
        if _is_duplicate(attr.name, base_taxonomy_names):
            continue

        score = _score_one(attr, base_taxonomy_names, total_signals)
        ranked.append(RankedAttribute(attr=attr, composite_score=score))

    # Sort descending by composite score, then by name for deterministic tie-breaking
    ranked.sort(key=lambda ra: (-ra.composite_score, ra.attr.name))

    return ranked[:top_n]
