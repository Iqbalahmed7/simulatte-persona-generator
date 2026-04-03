from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    n_raw_signals: int
    n_unique_signals: int           # after exact dedup
    n_near_duplicates_removed: int  # near-duplicates caught by trigram Jaccard
    n_valid_signals: int            # after all dedup
    is_valid: bool                  # True when n_valid_signals >= 200
    proxy_mode_suggested: bool      # True when n_valid_signals < 200
    recommendation: str             # human-readable guidance string

    def summary(self) -> str:
        return (
            f"{self.n_valid_signals}/{self.n_raw_signals} valid signals "
            f"(is_valid={self.is_valid}): {self.recommendation}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _trigrams(text: str) -> set[str]:
    """Return character trigrams for a string."""
    text = text.lower().strip()
    if len(text) < 3:
        return {text}
    return {text[i:i + 3] for i in range(len(text) - 2)}


def _trigram_jaccard(a: str, b: str) -> float:
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _near_dedup(signals: list[str]) -> list[str]:
    """
    O(n²) near-duplicate removal using trigram Jaccard similarity.

    For each pair (i, j) where i < j, if similarity > 0.85, mark the shorter
    signal for removal.  If both are equal length, mark j.  Operates on the
    input list in one pass and returns the surviving signals.
    """
    marked: set[int] = set()
    n = len(signals)
    for i in range(n):
        if i in marked:
            continue
        for j in range(i + 1, n):
            if j in marked:
                continue
            if _trigram_jaccard(signals[i], signals[j]) > 0.85:
                # Keep the longer one; on tie keep i (mark j)
                if len(signals[i]) >= len(signals[j]):
                    marked.add(j)
                else:
                    marked.add(i)
                    break  # i is now marked; no need to compare i further
    return [s for idx, s in enumerate(signals) if idx not in marked]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_corpus(signals: list[str]) -> ValidationReport:
    """
    Validate a list of signal strings for grounding readiness.

    Steps:
    1. Exact dedup  — use set() to remove exact duplicates.
    2. Near-dedup   — trigram Jaccard > 0.85 → keep longer (or first if equal).
    3. Count n_valid_signals = len(deduplicated list).
    4. is_valid = n_valid_signals >= 200.
    5. proxy_mode_suggested = not is_valid.
    6. recommendation at 3 thresholds:
       - n_valid < 50:        "Insufficient data …"
       - 50 <= n_valid < 200: "Below threshold …"
       - n_valid >= 200:      "Ready for grounding …"
    """
    n_raw = len(signals)

    # Step 1 — exact dedup (preserve a stable order via dict keys)
    seen: dict[str, None] = {}
    for s in signals:
        seen.setdefault(s, None)
    exact_deduped: list[str] = list(seen.keys())
    n_unique = len(exact_deduped)

    # Step 2 — near-dedup
    near_deduped = _near_dedup(exact_deduped)
    n_near_removed = n_unique - len(near_deduped)

    # Step 3-5
    n_valid = len(near_deduped)
    is_valid = n_valid >= 200
    proxy_mode_suggested = not is_valid

    # Step 6 — recommendation
    if n_valid < 50:
        recommendation = (
            "Insufficient data — minimum 200 signals required. "
            "Consider collecting more reviews or switching to proxy mode."
        )
    elif n_valid < 200:
        recommendation = (
            f"Below threshold — {n_valid} signals collected, 200 required. "
            "Proxy mode available but grounding quality will be limited."
        )
    else:
        recommendation = f"Ready for grounding — {n_valid} signals collected."

    return ValidationReport(
        n_raw_signals=n_raw,
        n_unique_signals=n_unique,
        n_near_duplicates_removed=n_near_removed,
        n_valid_signals=n_valid,
        is_valid=is_valid,
        proxy_mode_suggested=proxy_mode_suggested,
        recommendation=recommendation,
    )
