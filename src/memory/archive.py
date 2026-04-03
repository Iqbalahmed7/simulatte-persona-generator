"""src/memory/archive.py

Three-tier memory archive schema for hierarchical memory archival.
Activated only when working memory exceeds 1,000 observations (100+ turn simulations).
Deterministic — no LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ArchiveTier(str, Enum):
    ACTIVE = "active"
    WORKING_ARCHIVE = "working_archive"
    DEEP_ARCHIVE = "deep_archive"


@dataclass
class ArchiveEntry:
    id: str
    tier: ArchiveTier
    original_observation_ids: list[str]
    summary_content: str  # empty string until summarisation runs
    mean_importance: float
    earliest_timestamp: datetime
    latest_timestamp: datetime
    last_accessed: datetime
    citation_count: int = 0
    raw_content: str = ""  # populated by archival_engine when promoting; consumed by summarisation_engine


class ArchivalIndex(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    working_archive: list[ArchiveEntry] = Field(default_factory=list)
    deep_archive: list[ArchiveEntry] = Field(default_factory=list)
    total_compressed: int = 0
    last_archival_run: datetime | None = None
