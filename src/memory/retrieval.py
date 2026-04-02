"""
retrieval.py — Deterministic retrieval scoring for Simulatte working memory.

Implements the retrieval formula from Master Spec §8 (Generative Agents, Park et al.):
    score(entry) = α·recency + β·importance + γ·relevance

No LLM calls. Pure math + keyword overlap.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from src.schema.persona import Observation, Reflection

# ---------------------------------------------------------------------------
# Tunable weights (Open Questions O6, O7 — set defaults, allow override)
# ---------------------------------------------------------------------------
DEFAULT_ALPHA: float = 1 / 3          # recency weight
DEFAULT_BETA: float = 1 / 3           # importance weight
DEFAULT_GAMMA: float = 1 / 3          # relevance weight
DEFAULT_DECAY_LAMBDA: float = 0.01    # slow exponential decay (Open Question O7)

# ---------------------------------------------------------------------------
# Minimal inline stopword set — no NLTK dependency
# ---------------------------------------------------------------------------
_STOPWORDS: set[str] = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "of",
    "and", "or", "but", "for", "with", "this", "that", "was", "are",
    "be", "been", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "not", "no", "i", "my", "you", "your",
    "they", "their", "we", "our", "he", "she", "his", "her",
}


def _tokenise(text: str) -> set[str]:
    """Lowercase, split on whitespace/punctuation, strip stopwords."""
    import re
    tokens = re.findall(r"[a-zA-Z0-9']+", text.lower())
    return {t for t in tokens if t not in _STOPWORDS}


# ---------------------------------------------------------------------------
# Component scorers
# ---------------------------------------------------------------------------

def recency_score(
    entry: Observation | Reflection,
    now: datetime,
    decay_lambda: float = DEFAULT_DECAY_LAMBDA,
) -> float:
    """
    Exponential decay based on time since last access.

    recency = exp(-λ · hours_since_last_access)

    Returns a value in (0, 1].  Never negative.
    """
    delta_seconds = (now - entry.last_accessed).total_seconds()
    # Guard against clock skew producing tiny negative deltas
    hours = max(delta_seconds, 0.0) / 3600.0
    return math.exp(-decay_lambda * hours)


def importance_score(entry: Observation | Reflection) -> float:
    """
    Normalise importance (1–10) to [0.0, 1.0].

    importance_score = entry.importance / 10.0
    """
    return entry.importance / 10.0


def relevance_score(entry: Observation | Reflection, query: str) -> float:
    """
    Keyword overlap between query and entry content.

    relevance = |query_words ∩ content_words| / max(|query_words|, 1)

    Returns 0.0 if query has no meaningful tokens (all stopwords / empty).
    """
    query_words = _tokenise(query)
    if not query_words:
        return 0.0
    content_words = _tokenise(entry.content)
    overlap = query_words & content_words
    return len(overlap) / len(query_words)


# ---------------------------------------------------------------------------
# Composite scorer
# ---------------------------------------------------------------------------

def score_entry(
    entry: Observation | Reflection,
    query: str,
    now: datetime,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    gamma: float = DEFAULT_GAMMA,
    decay_lambda: float = DEFAULT_DECAY_LAMBDA,
) -> float:
    """
    Compute retrieval score for a single memory entry.

    score = α·recency(entry) + β·importance(entry) + γ·relevance(entry, query)

    With default α=β=γ=1/3 the weights sum to 1 and the score is in [0, 1].
    """
    r = recency_score(entry, now, decay_lambda)
    imp = importance_score(entry)
    rel = relevance_score(entry, query)
    return alpha * r + beta * imp + gamma * rel


# ---------------------------------------------------------------------------
# Top-K retrieval
# ---------------------------------------------------------------------------

def retrieve_top_k(
    entries: list[Observation | Reflection],
    query: str,
    k: int,
    now: datetime | None = None,
) -> list[Observation | Reflection]:
    """
    Score all entries, return top-K sorted descending by score.

    Does NOT update last_accessed — that is WorkingMemoryManager's responsibility.

    If k >= len(entries) all entries are returned, sorted by score descending.
    If entries is empty, returns [].
    """
    if not entries:
        return []

    if now is None:
        now = datetime.now(timezone.utc)

    scored = [(score_entry(e, query, now), e) for e in entries]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [e for _, e in scored[:k]]
