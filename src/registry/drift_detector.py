"""src/registry/drift_detector.py — ICP demographic drift detection.

Detects when a persona's real age has drifted outside an ICP's target age band.
Uses RegistryEntry.registered_at + RegistryEntry.age to compute current age.

No LLM calls. Deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional


try:
    from src.registry.persona_registry import RegistryEntry
except ImportError:
    RegistryEntry = None  # type: ignore[assignment, misc]


@dataclass
class DriftResult:
    persona_id: str
    age_at_registration: int     # entry.age
    current_age: int             # computed: age_at_registration + full years elapsed
    years_elapsed: float         # precise decimal years since registration
    icp_age_min: int
    icp_age_max: int
    is_drifted: bool             # True if current_age < icp_age_min OR > icp_age_max


def _parse_registered_at(registered_at: str) -> datetime:
    """Parse ISO datetime string to datetime (UTC). Handles both offset-aware and naive."""
    dt = datetime.fromisoformat(registered_at)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _years_elapsed(registered_at_dt: datetime, current_date: date) -> float:
    """Compute precise decimal years between registered_at and current_date."""
    delta_days = (current_date - registered_at_dt.date()).days
    return delta_days / 365.25


def _full_years_elapsed(registered_at_dt: datetime, current_date: date) -> int:
    """Compute full completed calendar years between registered_at and current_date.

    Uses birthday-style arithmetic so that exact anniversaries count as a full year.
    E.g. 2024-04-03 → 2026-04-03 = 2 full years (regardless of leap-year day counts).
    """
    reg_date = registered_at_dt.date()
    years = current_date.year - reg_date.year
    # Subtract one if the anniversary hasn't occurred yet this year
    if (current_date.month, current_date.day) < (reg_date.month, reg_date.day):
        years -= 1
    return years


def detect_drift(
    entry,  # RegistryEntry
    icp_age_min: int,
    icp_age_max: int,
    current_date: date | None = None,
) -> DriftResult:
    """Detect whether a persona has aged out of an ICP's age band.

    Parameters
    ----------
    entry:          RegistryEntry from the registry
    icp_age_min:    Minimum ICP age (inclusive)
    icp_age_max:    Maximum ICP age (inclusive)
    current_date:   Date to use as "today" (default: today UTC)
    """
    if current_date is None:
        current_date = date.today()

    registered_at_dt = _parse_registered_at(entry.registered_at)
    years = _years_elapsed(registered_at_dt, current_date)
    current_age = entry.age + _full_years_elapsed(registered_at_dt, current_date)
    is_drifted = current_age < icp_age_min or current_age > icp_age_max

    return DriftResult(
        persona_id=entry.persona_id,
        age_at_registration=entry.age,
        current_age=current_age,
        years_elapsed=years,
        icp_age_min=icp_age_min,
        icp_age_max=icp_age_max,
        is_drifted=is_drifted,
    )


def filter_drifted(
    entries: list,  # list[RegistryEntry]
    icp_age_min: int,
    icp_age_max: int,
    current_date: date | None = None,
) -> tuple[list, list]:  # (valid_entries, drifted_entries)
    """Split entries into valid (within ICP age band) and drifted (outside age band).

    Returns (valid_entries, drifted_entries).
    valid_entries: entries whose current_age is within [icp_age_min, icp_age_max]
    drifted_entries: entries whose current_age is outside that range
    """
    valid: list = []
    drifted: list = []

    for entry in entries:
        result = detect_drift(entry, icp_age_min, icp_age_max, current_date)
        if result.is_drifted:
            drifted.append(entry)
        else:
            valid.append(entry)

    return valid, drifted
