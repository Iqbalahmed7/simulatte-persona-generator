from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import time


@dataclass(frozen=True)
class GateWaiver:
    gate_id: Literal["G6", "G7", "G8", "G9", "G10", "G11"]
    attempts_made: int
    final_failure_reason: str
    confidence_penalty: float
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "gate_id": self.gate_id,
            "attempts_made": self.attempts_made,
            "final_failure_reason": self.final_failure_reason,
            "confidence_penalty": self.confidence_penalty,
            "timestamp": self.timestamp,
        }


def cumulative_penalty(waivers: list[GateWaiver]) -> float:
    """Sum of waiver penalties, capped at 0.5."""
    return min(0.5, sum(w.confidence_penalty for w in waivers))


def build_gate_waiver(
    gate_id: Literal["G6", "G7", "G8", "G9", "G10", "G11"],
    *,
    attempts_made: int,
    final_failure_reason: str,
    confidence_penalty: float = 0.1,
) -> GateWaiver:
    """Construct a GateWaiver with a current timestamp."""
    return GateWaiver(
        gate_id=gate_id,
        attempts_made=attempts_made,
        final_failure_reason=final_failure_reason,
        confidence_penalty=confidence_penalty,
        timestamp=time.time(),
    )
