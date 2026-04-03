"""src/schema/memory_extended.py

WorkingMemoryExtended: drop-in superset of WorkingMemory that adds an optional
ArchivalIndex. When archival_index is None, behaviour is identical to WorkingMemory.
"""

from __future__ import annotations

from src.schema.persona import WorkingMemory
from src.memory.archive import ArchivalIndex


class WorkingMemoryExtended(WorkingMemory):
    """
    Strict superset of WorkingMemory.  Adds one optional field: archival_index.
    Any code that accepts WorkingMemory also accepts WorkingMemoryExtended without
    modification.  When archival_index is None the behaviour is identical to
    WorkingMemory.
    """

    archival_index: ArchivalIndex | None = None

    model_config = {"arbitrary_types_allowed": True}
