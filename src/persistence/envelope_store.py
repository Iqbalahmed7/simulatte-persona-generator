"""CohortEnvelope JSON persistence.

Sprint 12. Saves and loads CohortEnvelope to/from JSON files.
Uses model_dump() for serialisation and model_validate() for deserialisation.

Sprint 24 addition: type-guarded archival serialisation path. When a persona's
memory.working field is a WorkingMemoryExtended instance, ArchiveStore.to_json()
and from_json() are used transparently.  Standard WorkingMemory instances follow
the original code path unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _serialise_envelope_data(envelope: Any) -> dict:
    """Return a JSON-serialisable dict for *envelope*.

    For each persona in the envelope, if ``memory.working`` is a
    ``WorkingMemoryExtended`` instance the archival-aware serialiser is used;
    otherwise the standard ``model_dump(mode="json")`` path is taken.

    This is an internal helper — callers do not need to know about archival.
    """
    from src.schema.memory_extended import WorkingMemoryExtended
    from src.memory.archive_store import ArchiveStore

    data = envelope.model_dump(mode="json")

    # Walk personas and replace working memory dicts when the live object is
    # WorkingMemoryExtended so that the archival_index survives round-trips.
    for i, persona in enumerate(envelope.personas):
        working = persona.memory.working
        if isinstance(working, WorkingMemoryExtended):
            data["personas"][i]["memory"]["working"] = ArchiveStore.to_json(working)

    return data


def _deserialise_working_memory(working_data: dict) -> Any:
    """Reconstruct a working memory object from a raw dict.

    If the dict contains an ``"archival_index"`` key (even if its value is
    ``None``) the archival-aware deserialiser is used, returning a
    ``WorkingMemoryExtended``.  Legacy dicts that lack the key are returned as
    standard ``WorkingMemory`` via the normal Pydantic validation path.
    """
    if "archival_index" in working_data:
        from src.memory.archive_store import ArchiveStore
        return ArchiveStore.from_json(working_data)
    # Legacy path — standard WorkingMemory
    from src.schema.persona import WorkingMemory
    return WorkingMemory.model_validate(working_data)


def save_envelope(envelope: Any, path: str | Path) -> Path:
    """Serialise a CohortEnvelope to a JSON file.

    Args:
        envelope: A CohortEnvelope instance.
        path: Destination file path (created or overwritten).

    Returns:
        The resolved Path where the file was written.
    """
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    data = _serialise_envelope_data(envelope)
    with open(resolved, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return resolved


def load_envelope(path: str | Path) -> Any:
    """Load a CohortEnvelope from a JSON file.

    Args:
        path: Path to a JSON file previously written by save_envelope().

    Returns:
        A CohortEnvelope instance.  Personas whose working memory JSON contains
        an ``"archival_index"`` key are loaded as WorkingMemoryExtended;
        legacy personas without that key load as standard WorkingMemory.

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

    # Pre-process working memory fields before full Pydantic validation so that
    # archival-extended personas survive the round-trip.
    for persona_data in data.get("personas", []):
        working_data = persona_data.get("memory", {}).get("working")
        if isinstance(working_data, dict) and "archival_index" in working_data:
            # Replace the raw dict with a reconstructed WorkingMemoryExtended so
            # Pydantic picks it up correctly as the working field.
            persona_data["memory"]["working"] = _deserialise_working_memory(
                working_data
            ).model_dump()

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
