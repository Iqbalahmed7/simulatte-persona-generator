"""src/schema/calibration_card.py

CalibrationCard — the front-page believability proof attached to every
Niobe / Morpheus deliverable (Spec 02 — Calibration Card).

Design notes
------------
- Mirrors the dataclass + constants pattern from src/schema/receipt.py
  (Spec 03 — Glass Box Provenance), so the two artifacts feel like siblings.
- Schema version is shared with ResponseReceipt: "2026-05-01".
- Calibration metric headline: **mean_absolute_error on top-line distributions**.
  Rationale: MAE is interpretable to a CPG buyer ("off by X percentage points")
  and directly comparable across studies. KL divergence is more theoretically
  complete but opaque to non-statisticians. Revisit if cross-study meta-analysis
  demands a proper information-theoretic metric.
- The card is NON-OPTIONAL. Every deliverable ships with one. If Iris has no
  benchmark data, calibration_status is "uncalibrated" and the honest_disclaimer
  says so — we never fake numbers.
- workspace_id is intentionally absent: the card is workspace-locked by the
  study it describes. No cross-workspace pooling (anti-goal from README).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

CALIBRATION_CARD_SCHEMA_VERSION = "2026-05-01"

# Calibration metric choice — see module docstring for rationale.
# Stored as a Literal so the dashboard can gate on it and we can detect
# if someone changes it mid-flight.
CalibrationMetric = Literal["mean_absolute_error"]

CalibrationStatus = Literal["calibrated", "partial", "uncalibrated"]

BenchmarkType = Literal[
    "census",
    "gwi",
    "syndicated",
    "client_first_party",
    "academic",
]

CoverageCalibrationStatus = Literal["calibrated", "extrapolated", "novel"]


@dataclass
class BenchmarkSource:
    """One real-world data source used to calibrate this study."""

    name: str
    # e.g. "US Census 2020 ACS", "GWI Core Q4 2024", "Client Brand Tracker Wave 3"
    type: BenchmarkType
    citation: str
    # Citation in the format the research team already uses (APA, short-form, etc.)
    reference_url: str | None = None


@dataclass
class CoverageSegment:
    """Calibration status for one segment of the study brief.

    confidence_delta: positive = model is more confident than benchmark would
    predict; negative = less confident; None = no benchmark to compare against.
    """

    segment_name: str
    calibration_status: CoverageCalibrationStatus
    confidence_delta: float | None = None


@dataclass
class CalibrationCard:
    """One-page believability proof — the FRONT page of every deliverable.

    Fields
    ------
    schema_version
        Locked to CALIBRATION_CARD_SCHEMA_VERSION. Change triggers a versioning
        bump so consumers can detect schema drift.
    study_id
        The run_id / cohort_id of the study this card belongs to.
    generated_at
        UTC timestamp of card generation (stamped by build_calibration_card).
    calibration_metric
        Always "mean_absolute_error" for now. Stored explicitly so the dashboard
        can render the right label and we can detect a metric change at parse time.
    calibration_score
        Mean absolute error between Simulatte's top-line distributions and
        benchmark ground truth, expressed as a fraction (0.05 = 5 pp off).
        None when calibration_status == "uncalibrated".
    calibration_status
        "calibrated"   — Iris ran, benchmarks exist, score is populated.
        "partial"      — Iris ran but only subset of segments had benchmarks.
        "uncalibrated" — No benchmark data for this study type; score is None.
    benchmark_sources
        Explicit, citable data sources. Empty list is valid for uncalibrated
        studies; the honest_disclaimer should explain why.
    coverage_map
        Per-segment calibration breakdown. Populated from the study's
        PopulationSpec / CohortEnvelope segments.
    known_limitations
        Explicit list of where this calibration breaks. Required field — an
        empty list is a red flag and should be avoided in production.
    foundation_version
        The PopScale foundation snapshot this study ran on.
        TODO: read from PopScale's foundation snapshot once that API is stable
        (same TODO as ResponseReceipt.foundation_version in Spec 03).
    iris_run_id
        Traceability pointer into Iris if a calibration run was executed.
        None when Iris has no benchmark data for this study type.
    honest_disclaimer
        Plain-English statement of what this card does and does not claim.
        Required. The card must not be silent about its own limitations.
    """

    schema_version: str = CALIBRATION_CARD_SCHEMA_VERSION
    study_id: str = ""
    generated_at: datetime = field(default_factory=lambda: __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ))

    # Metric choice — locked; see module docstring
    calibration_metric: CalibrationMetric = "mean_absolute_error"

    # Score is None when uncalibrated — never fake a number
    calibration_score: float | None = None
    calibration_status: CalibrationStatus = "uncalibrated"

    benchmark_sources: list[BenchmarkSource] = field(default_factory=list)
    coverage_map: list[CoverageSegment] = field(default_factory=list)
    known_limitations: list[str] = field(default_factory=list)

    # Foundation snapshot version — None until PopScale exposes this field
    foundation_version: str | None = None

    # Iris traceability — None when Iris has no data for this study type
    iris_run_id: str | None = None

    honest_disclaimer: str = (
        "This card declares match/miss honestly. "
        "Where ground truth exists, we report it. "
        "Where it does not, we say so."
    )
