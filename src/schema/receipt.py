from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RECEIPT_SCHEMA_VERSION = "2026-05-01"
OOD_CONFIDENCE_THRESHOLD = 40
LOW_CONSISTENCY_THRESHOLD = 40
NOISE_FLAG_THRESHOLD = 15

# influence_direction is None for signals whose effect depends on the question
# being asked (e.g. trust_orientation, life_stage). Only set for inherently
# directional signals (price/risk/switching).
InfluenceDirection = Literal["toward", "against", "neutral"]


@dataclass
class SignalTrace:
    signal_name: str
    signal_category: Literal["demographic", "behavioral", "psychographic", "memory"]
    signal_value: str
    influence_direction: InfluenceDirection | None = None


@dataclass
class ArchetypeAnchor:
    decision_style: str
    value_orientation: str
    active_tendencies: list[str]


@dataclass
class ResponseReceipt:
    schema_version: str = RECEIPT_SCHEMA_VERSION
    source_signals: list[SignalTrace] = field(default_factory=list)
    archetype_anchor: ArchetypeAnchor | None = None
    confidence_score: int = 0
    confidence_flags: list[str] = field(default_factory=list)
    out_of_distribution: bool = False
    ood_reason: str | None = None
    noise_applied: int | None = None
    foundation_version: str | None = None
