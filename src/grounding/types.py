"""Shared type definitions for the Grounding Pipeline.

Sprint 8 — Grounding Pipeline.
No LLM calls. Pure data types only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# --- Signal types ---

SignalType = Literal[
    "purchase_trigger",
    "rejection",
    "switching",
    "trust_citation",
    "price_mention",
]


@dataclass
class Signal:
    """A single decision-language signal extracted from raw text."""
    id: str
    text: str
    signal_type: SignalType
    platform: str | None = None
    rating: int | None = None    # 1–5 star rating if available
    date: str | None = None
    category: str | None = None


# --- Feature types ---

@dataclass
class BehaviouralFeatures:
    """Aggregate behavioural features computed from a Signal list.

    All proportion fields must be in [0.0, 1.0].
    """
    price_salience_index: float          # price_mention count / total signals
    trust_source_distribution: dict[str, float]   # expert/peer/brand/ad/community keys
    switching_trigger_taxonomy: dict[str, float]  # price/feature/service/competitive/life_change
    purchase_trigger_taxonomy: dict[str, float]   # need/recommendation/trial/promotion/event
    objection_cluster_frequencies: dict[str, float]  # price/trust/information keys
    signal_count: int

    def to_vector(self) -> list[float]:
        """Flatten to a fixed 9-dim vector for clustering input.

        Dimensions (in order):
          0: price_salience_index
          1: trust_source_distribution["expert"]
          2: trust_source_distribution["peer"]
          3: trust_source_distribution["brand"]
          4: trust_source_distribution["community"]
          5: switching_trigger_taxonomy["price"]
          6: switching_trigger_taxonomy["service"]
          7: purchase_trigger_taxonomy["need"]
          8: purchase_trigger_taxonomy["recommendation"]
        """
        td = self.trust_source_distribution
        sw = self.switching_trigger_taxonomy
        pt = self.purchase_trigger_taxonomy
        return [
            self.price_salience_index,
            td.get("expert", 0.0),
            td.get("peer", 0.0),
            td.get("brand", 0.0),
            td.get("community", 0.0),
            sw.get("price", 0.0),
            sw.get("service", 0.0),
            pt.get("need", 0.0),
            pt.get("recommendation", 0.0),
        ]


# --- Archetype types ---

@dataclass
class BehaviouralArchetype:
    """A behavioural cluster archetype derived from GMM or K-means clustering."""
    archetype_id: str
    size: int                                    # number of signals in this cluster
    price_sensitivity_band: Literal["low", "medium", "high", "extreme"]
    trust_orientation_weights: dict[str, float]  # expert/peer/brand/ad/community/influencer
    switching_propensity_band: Literal["low", "medium", "high"]
    primary_objections: list[str]
    centroid: list[float]                        # 9-dim feature vector centroid


# --- Pipeline result ---

@dataclass
class GroundingResult:
    """Result of running the full grounding pipeline."""
    personas: list                           # list[PersonaRecord] — updated with grounded tendencies
    archetypes: list[BehaviouralArchetype]
    signals_extracted: int
    clusters_derived: int
    warning: str | None = None               # populated if signal_count < 200
