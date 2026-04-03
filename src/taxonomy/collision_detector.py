"""src/taxonomy/collision_detector.py

Deterministic, LLM-free collision detection between ICP anchor traits and
the base taxonomy / domain template attribute names.

Three collision types are detected per anchor trait:
  - exact            : case-insensitive equality with a base taxonomy name
  - near_duplicate   : token-Jaccard similarity > 0.6 with a base taxonomy name
                       (not already flagged as exact)
  - template_collision: case-insensitive equality with a domain template name

The module is importable independently — it has no dependency on the parser.

Spec ref: Sprint 26 — collision detection layer for ICP anchor traits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CollisionEntry:
    attribute_name: str      # the ICP anchor trait that collided
    collision_type: str      # "exact", "near_duplicate", "template_collision"
    collided_with: str       # name of the base/template attr it collided with
    jaccard_similarity: float  # 1.0 for exact, computed for near_duplicate,
                               # 0.0 for template_collision


@dataclass
class CollisionReport:
    exact_collisions: list[CollisionEntry] = field(default_factory=list)
    near_duplicate_collisions: list[CollisionEntry] = field(default_factory=list)
    template_collisions: list[CollisionEntry] = field(default_factory=list)

    @property
    def has_collisions(self) -> bool:
        return bool(
            self.exact_collisions
            or self.near_duplicate_collisions
            or self.template_collisions
        )

    def summary(self) -> str:
        parts = []
        if self.exact_collisions:
            parts.append(f"{len(self.exact_collisions)} exact collision(s)")
        if self.near_duplicate_collisions:
            parts.append(f"{len(self.near_duplicate_collisions)} near-duplicate(s)")
        if self.template_collisions:
            parts.append(f"{len(self.template_collisions)} template collision(s)")
        return "; ".join(parts) if parts else "no collisions"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _jaccard(a: str, b: str) -> float:
    """Token-based Jaccard similarity.

    Tokenises both strings by replacing underscores with spaces and splitting
    on whitespace, then computes |intersection| / |union| on the token sets.
    """
    tokens_a = set(a.lower().replace("_", " ").split())
    tokens_b = set(b.lower().replace("_", " ").split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_collisions(
    icp_anchor_traits: list[str],
    base_taxonomy_names: list[str],
    template_attributes: list[str],
) -> CollisionReport:
    """Detect collisions between ICP anchor traits and known attribute names.

    Args:
        icp_anchor_traits:   Attribute names taken from the ICP spec anchor_traits
                             list.
        base_taxonomy_names: All attribute names from the base taxonomy
                             (typically ``[a.name for a in BASE_TAXONOMY]``).
        template_attributes: Attribute names from the selected domain template.
                             Pass ``[]`` when template selection has not yet
                             occurred (e.g. at parse time).

    Returns:
        A :class:`CollisionReport` with three categorised lists.

    Detection rules
    ---------------
    1. **exact** — ``anchor_trait.lower() == base_name.lower()``
    2. **near_duplicate** — token-Jaccard(anchor_trait, base_name) > 0.6
       *and* the pair is not already flagged as exact.  When multiple base
       names qualify, the one with the highest similarity score is recorded.
    3. **template_collision** — ``anchor_trait.lower() == template_name.lower()``

    A single anchor trait may appear in more than one collision category.
    """
    report = CollisionReport()

    # Normalised lookup sets / lists built once for efficiency.
    base_lower: list[str] = [n.lower() for n in base_taxonomy_names]
    template_lower: set[str] = {n.lower() for n in template_attributes}

    for trait in icp_anchor_traits:
        trait_lower = trait.lower()

        # ------------------------------------------------------------------ #
        # 1. Exact collision against base taxonomy
        # ------------------------------------------------------------------ #
        exact_match: Optional[str] = None
        for orig, norm in zip(base_taxonomy_names, base_lower):
            if trait_lower == norm:
                exact_match = orig
                break

        if exact_match is not None:
            report.exact_collisions.append(
                CollisionEntry(
                    attribute_name=trait,
                    collision_type="exact",
                    collided_with=exact_match,
                    jaccard_similarity=1.0,
                )
            )

        # ------------------------------------------------------------------ #
        # 2. Near-duplicate collision against base taxonomy
        #    (only when there is no exact match for this trait)
        # ------------------------------------------------------------------ #
        if exact_match is None:
            best_score: float = 0.0
            best_name: Optional[str] = None

            for orig in base_taxonomy_names:
                score = _jaccard(trait, orig)
                if score > best_score:
                    best_score = score
                    best_name = orig

            if best_score > 0.6 and best_name is not None:
                report.near_duplicate_collisions.append(
                    CollisionEntry(
                        attribute_name=trait,
                        collision_type="near_duplicate",
                        collided_with=best_name,
                        jaccard_similarity=best_score,
                    )
                )

        # ------------------------------------------------------------------ #
        # 3. Template collision
        # ------------------------------------------------------------------ #
        if trait_lower in template_lower:
            # Recover original casing from template_attributes
            collided_with = next(
                t for t in template_attributes if t.lower() == trait_lower
            )
            report.template_collisions.append(
                CollisionEntry(
                    attribute_name=trait,
                    collision_type="template_collision",
                    collided_with=collided_with,
                    jaccard_similarity=0.0,
                )
            )

    return report


__all__ = [
    "CollisionEntry",
    "CollisionReport",
    "detect_collisions",
]
