"""tests/fixtures/synthetic_observation.py — Factory for synthetic Observation objects.

Used by BV1 and BV2 tests. No LLM calls. All timestamps use datetime.now(timezone.utc).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.schema.persona import Observation


def make_synthetic_observation(
    content: str,
    importance: int = 5,
    emotional_valence: float = 0.0,
) -> Observation:
    """
    Create a minimal valid Observation for use in BV tests.

    Args:
        content: The observation text content.
        importance: Integer 1-10 (default 5).
        emotional_valence: Float -1.0 to 1.0 (default 0.0).

    Returns:
        A fully valid Observation with a fresh uuid4 id and UTC timestamp.
    """
    now = datetime.now(timezone.utc)
    return Observation(
        id=str(uuid.uuid4()),
        timestamp=now,
        type="observation",
        content=content,
        importance=importance,
        emotional_valence=emotional_valence,
        source_stimulus_id=None,
        last_accessed=now,
    )
