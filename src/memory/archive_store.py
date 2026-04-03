"""src/memory/archive_store.py

Serialisation/deserialisation for WorkingMemoryExtended with ArchivalIndex.
Backward compatible: legacy JSON with no archival_index key deserialises with archival_index=None.
"""
from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any

from src.schema.persona import WorkingMemory
from src.schema.memory_extended import WorkingMemoryExtended
from src.memory.archive import ArchivalIndex, ArchiveEntry, ArchiveTier


class ArchiveStore:
    """Static helpers for attaching/detaching ArchivalIndex and round-trip JSON
    serialisation of WorkingMemoryExtended.

    No LLM calls.  All methods are pure functions exposed as class-level statics.
    """

    # ------------------------------------------------------------------
    # attach / detach
    # ------------------------------------------------------------------

    @staticmethod
    def attach_index(memory: WorkingMemory) -> WorkingMemoryExtended:
        """Wrap a standard WorkingMemory into WorkingMemoryExtended with an empty
        ArchivalIndex.

        Args:
            memory: A WorkingMemory (or WorkingMemoryExtended) instance.

        Returns:
            WorkingMemoryExtended with archival_index initialised to an empty
            ArchivalIndex().
        """
        return WorkingMemoryExtended(
            **memory.model_dump(), archival_index=ArchivalIndex()
        )

    @staticmethod
    def detach_index(
        memory: WorkingMemoryExtended,
    ) -> tuple[WorkingMemory, ArchivalIndex | None]:
        """Separate a WorkingMemoryExtended back into its base WorkingMemory and the
        ArchivalIndex.

        Args:
            memory: A WorkingMemoryExtended instance.

        Returns:
            A 2-tuple of (WorkingMemory, ArchivalIndex | None).
        """
        base_fields = {
            k: v for k, v in memory.model_dump().items() if k != "archival_index"
        }
        return WorkingMemory(**base_fields), memory.archival_index

    # ------------------------------------------------------------------
    # serialisation
    # ------------------------------------------------------------------

    @staticmethod
    def to_json(memory: WorkingMemoryExtended) -> dict:
        """Fully serialise a WorkingMemoryExtended to a plain dict suitable for
        json.dump().

        Handles:
        - datetime fields → ISO 8601 strings
        - ArchiveEntry dataclass instances → plain dicts via dataclasses.asdict(),
          with nested datetime fields converted to ISO strings and ArchiveTier enum
          converted to its string value.

        Args:
            memory: A WorkingMemoryExtended instance.

        Returns:
            A JSON-serialisable dict.
        """
        # Use Pydantic's mode="json" for the base fields (handles datetime, etc.)
        data: dict[str, Any] = memory.model_dump(mode="json", exclude={"archival_index"})

        # Serialise archival_index separately so we can handle the ArchiveEntry
        # dataclasses correctly.
        if memory.archival_index is None:
            data["archival_index"] = None
        else:
            data["archival_index"] = ArchiveStore._serialise_archival_index(
                memory.archival_index
            )

        return data

    @staticmethod
    def _serialise_archival_index(index: ArchivalIndex) -> dict:
        """Convert an ArchivalIndex to a plain dict."""
        return {
            "working_archive": [
                ArchiveStore._serialise_archive_entry(e)
                for e in index.working_archive
            ],
            "deep_archive": [
                ArchiveStore._serialise_archive_entry(e)
                for e in index.deep_archive
            ],
            "total_compressed": index.total_compressed,
            "last_archival_run": (
                index.last_archival_run.isoformat()
                if index.last_archival_run is not None
                else None
            ),
        }

    @staticmethod
    def _serialise_archive_entry(entry: ArchiveEntry) -> dict:
        """Convert a single ArchiveEntry dataclass to a plain dict."""
        raw = dataclasses.asdict(entry)
        # dataclasses.asdict recurses but leaves datetime objects intact;
        # ArchiveTier enum values are left as enum members.
        raw["tier"] = entry.tier.value  # ArchiveTier → str
        for dt_field in ("earliest_timestamp", "latest_timestamp", "last_accessed"):
            if raw[dt_field] is not None:
                raw[dt_field] = (
                    raw[dt_field].isoformat()
                    if isinstance(raw[dt_field], datetime)
                    else raw[dt_field]
                )
        return raw

    # ------------------------------------------------------------------
    # deserialisation
    # ------------------------------------------------------------------

    @staticmethod
    def from_json(data: dict) -> WorkingMemoryExtended:
        """Deserialise a plain dict back into a WorkingMemoryExtended.

        Backward compatible: if the ``"archival_index"`` key is absent or its
        value is ``None``, ``archival_index`` is set to ``None`` without error.

        Args:
            data: A dict previously produced by :meth:`to_json` or a legacy JSON
                  dict that predates the archival_index field.

        Returns:
            A WorkingMemoryExtended instance.
        """
        # Pop archival_index before passing remaining keys to WorkingMemory
        archival_raw = data.get("archival_index")  # None if absent

        base_data = {k: v for k, v in data.items() if k != "archival_index"}
        # Validate the base fields via the Pydantic WorkingMemory schema which
        # already handles datetime coercion from ISO strings.
        base_memory = WorkingMemory.model_validate(base_data)

        if archival_raw is None:
            archival_index: ArchivalIndex | None = None
        else:
            archival_index = ArchiveStore._deserialise_archival_index(archival_raw)

        return WorkingMemoryExtended(
            **base_memory.model_dump(), archival_index=archival_index
        )

    @staticmethod
    def _deserialise_archival_index(raw: dict) -> ArchivalIndex:
        """Reconstruct an ArchivalIndex from a plain dict."""
        working_archive = [
            ArchiveStore._deserialise_archive_entry(e)
            for e in raw.get("working_archive", [])
        ]
        deep_archive = [
            ArchiveStore._deserialise_archive_entry(e)
            for e in raw.get("deep_archive", [])
        ]
        last_archival_run_raw = raw.get("last_archival_run")
        last_archival_run = (
            datetime.fromisoformat(last_archival_run_raw)
            if last_archival_run_raw is not None
            else None
        )
        return ArchivalIndex(
            working_archive=working_archive,
            deep_archive=deep_archive,
            total_compressed=raw.get("total_compressed", 0),
            last_archival_run=last_archival_run,
        )

    @staticmethod
    def _deserialise_archive_entry(raw: dict) -> ArchiveEntry:
        """Reconstruct an ArchiveEntry dataclass from a plain dict."""
        return ArchiveEntry(
            id=raw["id"],
            tier=ArchiveTier(raw["tier"]),
            original_observation_ids=raw["original_observation_ids"],
            summary_content=raw["summary_content"],
            mean_importance=float(raw["mean_importance"]),
            earliest_timestamp=datetime.fromisoformat(raw["earliest_timestamp"]),
            latest_timestamp=datetime.fromisoformat(raw["latest_timestamp"]),
            last_accessed=datetime.fromisoformat(raw["last_accessed"]),
            citation_count=int(raw.get("citation_count", 0)),
        )
