"""CohortEnvelope JSON persistence.

Sprint 12. Saves and loads CohortEnvelope to/from JSON files.
Uses model_dump() for serialisation and model_validate() for deserialisation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_envelope(envelope: Any, path: str | Path) -> Path:
    """Serialise a CohortEnvelope to a JSON file.

    Args:
        envelope: A CohortEnvelope instance.
        path: Destination file path (created or overwritten).

    Returns:
        The resolved Path where the file was written.
    """
    from src.schema.cohort import CohortEnvelope
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    data = envelope.model_dump(mode="json")
    with open(resolved, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return resolved


def load_envelope(path: str | Path) -> Any:
    """Load a CohortEnvelope from a JSON file.

    Args:
        path: Path to a JSON file previously written by save_envelope().

    Returns:
        A CohortEnvelope instance.

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the JSON cannot be parsed into a CohortEnvelope.
    """
    from src.schema.cohort import CohortEnvelope
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Envelope file not found: {resolved}")
    with open(resolved, "r", encoding="utf-8") as f:
        data = json.load(f)
    try:
        return CohortEnvelope.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Failed to parse envelope from {resolved}: {exc}") from exc


def envelope_summary(envelope: Any) -> str:
    """Return a brief human-readable summary of a CohortEnvelope.

    Used by CLI commands to print a one-line status after load/save.
    """
    n = len(envelope.personas)
    domain = envelope.domain
    cohort_id = envelope.cohort_id
    mode = envelope.mode
    return f"Cohort {cohort_id}: {n} persona(s), domain={domain}, mode={mode}"
