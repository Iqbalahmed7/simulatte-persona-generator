"""src/calibration/card_builder.py

build_calibration_card() — factory that produces a CalibrationCard for every
Niobe / Morpheus deliverable (Spec 02 — Calibration Card).

Contract
--------
- Deterministic: no LLM calls.
- Fails gracefully: if Iris outputs are absent or incomplete, emits
  calibration_status="uncalibrated" with an honest reason. Never returns None.
- Reads the study's cohort_envelope to populate the coverage map.
- Pulls foundation_version from the same cohort_envelope field used by
  ResponseReceipt (forward-compatible once PopScale exposes it).

IrisOutputs format (optional dict passed by callers who have run Iris)
-----------------------------------------------------------------------
{
    "iris_run_id": str,                    # required
    "calibration_score": float,            # MAE as a fraction, e.g. 0.07 = 7 pp
    "calibration_status": "calibrated" | "partial" | "uncalibrated",
    "benchmark_sources": [                 # list of dicts, one per BenchmarkSource
        {
            "name": str,
            "type": "census" | "gwi" | "syndicated" | "client_first_party" | "academic",
            "citation": str,
            "reference_url": str | None,
        },
        ...
    ],
    "known_limitations": [str, ...],       # optional; empty list is fine
}

Callers that have NOT run Iris pass iris_outputs=None.  The card will emit
with calibration_status="uncalibrated" and the honest reason.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.schema.calibration_card import (
    CALIBRATION_CARD_SCHEMA_VERSION,
    BenchmarkSource,
    CalibrationCard,
    CoverageSegment,
)

logger = logging.getLogger(__name__)

# Segments we always try to infer from a cohort envelope, in display order.
_STANDARD_SEGMENT_KEYS = (
    "age_group",
    "gender",
    "income_band",
    "location",
    "life_stage",
    "decision_style",
    "trust_anchor",
    "risk_appetite",
)


def build_calibration_card(
    study_id: str,
    cohort_envelope: dict,
    iris_outputs: dict | None = None,
) -> CalibrationCard:
    """Build and return a CalibrationCard for this study.

    Parameters
    ----------
    study_id:
        The run_id / cohort_id of the study (used as the card's study_id).
    cohort_envelope:
        The full CohortEnvelope dict produced by the generation pipeline.
        Used to populate the coverage map and foundation_version.
    iris_outputs:
        Optional dict of Iris calibration outputs (see module docstring).
        Pass None when Iris has no benchmark data for this study type.

    Returns
    -------
    CalibrationCard
        Always returns a populated card. Never returns None.
        calibration_status is "uncalibrated" when iris_outputs is absent.
    """
    generated_at = datetime.now(tz=timezone.utc)

    # ------------------------------------------------------------------
    # 1. Foundation version — same field as ResponseReceipt
    # ------------------------------------------------------------------
    # TODO: read from PopScale's foundation snapshot API once stable
    # (same TODO as Spec 03 ResponseReceipt.foundation_version)
    foundation_version: str | None = cohort_envelope.get("foundation_version") or None

    # ------------------------------------------------------------------
    # 2. Coverage map — inferred from cohort_envelope segments
    # ------------------------------------------------------------------
    coverage_map = _build_coverage_map(cohort_envelope, iris_outputs)

    # ------------------------------------------------------------------
    # 3. Calibration fields — from Iris if available, else uncalibrated
    # ------------------------------------------------------------------
    if iris_outputs is None:
        return CalibrationCard(
            schema_version=CALIBRATION_CARD_SCHEMA_VERSION,
            study_id=study_id,
            generated_at=generated_at,
            calibration_metric="mean_absolute_error",
            calibration_score=None,
            calibration_status="uncalibrated",
            benchmark_sources=[],
            coverage_map=coverage_map,
            known_limitations=[
                "No Iris benchmark run for this study type — calibration score unavailable.",
                "Coverage map segments are inferred from cohort structure, not validated against ground truth.",
            ],
            foundation_version=foundation_version,
            iris_run_id=None,
            honest_disclaimer=(
                "This card declares match/miss honestly. "
                "No ground-truth benchmark data was available for this study type. "
                "Calibration score is not reported rather than fabricated."
            ),
        )

    # ------------------------------------------------------------------
    # 4. Iris outputs present — validate and unpack
    # ------------------------------------------------------------------
    iris_run_id = iris_outputs.get("iris_run_id")
    raw_score = iris_outputs.get("calibration_score")
    raw_status = iris_outputs.get("calibration_status", "uncalibrated")
    raw_sources = iris_outputs.get("benchmark_sources", [])
    raw_limitations = iris_outputs.get("known_limitations", [])

    # Validate score is a float if provided
    calibration_score: float | None = None
    if raw_score is not None:
        try:
            calibration_score = float(raw_score)
        except (TypeError, ValueError):
            logger.warning(
                "build_calibration_card: iris_outputs['calibration_score'] is not numeric "
                "(%r); treating as uncalibrated.",
                raw_score,
            )
            raw_status = "uncalibrated"

    # Validate status is a known value
    valid_statuses = {"calibrated", "partial", "uncalibrated"}
    if raw_status not in valid_statuses:
        logger.warning(
            "build_calibration_card: unknown calibration_status %r from Iris; "
            "defaulting to 'uncalibrated'.",
            raw_status,
        )
        raw_status = "uncalibrated"
        calibration_score = None

    # If status is uncalibrated, score must be None (never fake numbers)
    if raw_status == "uncalibrated":
        calibration_score = None

    # ------------------------------------------------------------------
    # 5. Benchmark sources
    # ------------------------------------------------------------------
    benchmark_sources: list[BenchmarkSource] = []
    valid_types = {"census", "gwi", "syndicated", "client_first_party", "academic"}
    for src in raw_sources:
        src_type = src.get("type", "syndicated")
        if src_type not in valid_types:
            logger.warning(
                "build_calibration_card: unknown benchmark type %r; skipping source %r.",
                src_type,
                src.get("name"),
            )
            continue
        benchmark_sources.append(
            BenchmarkSource(
                name=src.get("name", "Unknown"),
                type=src_type,  # type: ignore[arg-type]
                citation=src.get("citation", ""),
                reference_url=src.get("reference_url"),
            )
        )

    # ------------------------------------------------------------------
    # 6. Known limitations — merge Iris list with any coverage gaps
    # ------------------------------------------------------------------
    known_limitations = list(raw_limitations)
    novel_segments = [
        seg.segment_name for seg in coverage_map
        if seg.calibration_status == "novel"
    ]
    if novel_segments:
        known_limitations.append(
            f"Novel segments (no prior calibration): {', '.join(novel_segments)}."
        )

    # ------------------------------------------------------------------
    # 7. Assemble card
    # ------------------------------------------------------------------
    return CalibrationCard(
        schema_version=CALIBRATION_CARD_SCHEMA_VERSION,
        study_id=study_id,
        generated_at=generated_at,
        calibration_metric="mean_absolute_error",
        calibration_score=calibration_score,
        calibration_status=raw_status,  # type: ignore[arg-type]
        benchmark_sources=benchmark_sources,
        coverage_map=coverage_map,
        known_limitations=known_limitations,
        foundation_version=foundation_version,
        iris_run_id=iris_run_id,
        honest_disclaimer=(
            "This card declares match/miss honestly. "
            "Where ground truth exists, we report it. "
            "Where it does not, we say so."
        ),
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_coverage_map(
    cohort_envelope: dict,
    iris_outputs: dict | None,
) -> list[CoverageSegment]:
    """Infer coverage map from cohort_envelope + Iris segment data.

    If Iris provides per-segment data, use it. Otherwise, derive segments
    from the cohort_envelope's anchor_overrides and cohort_summary, and
    mark them all as "extrapolated" (not novel — these are standard segments
    we model but haven't validated against a specific benchmark this run).
    """
    # If Iris supplied per-segment coverage, use that directly
    if iris_outputs and "coverage_map" in iris_outputs:
        segments = []
        for entry in iris_outputs["coverage_map"]:
            raw_cs = entry.get("calibration_status", "extrapolated")
            if raw_cs not in ("calibrated", "extrapolated", "novel"):
                raw_cs = "extrapolated"
            segments.append(
                CoverageSegment(
                    segment_name=entry.get("segment_name", "unknown"),
                    calibration_status=raw_cs,  # type: ignore[arg-type]
                    confidence_delta=entry.get("confidence_delta"),
                )
            )
        return segments

    # Derive from cohort envelope structure
    segments: list[CoverageSegment] = []

    # anchor_overrides tells us which dimensions were explicitly scoped
    anchor_overrides: dict = cohort_envelope.get("anchor_overrides", {}) or {}

    # cohort_summary tells us which distributions we actually generated
    cohort_summary: dict = cohort_envelope.get("cohort_summary", {}) or {}
    distribution_keys = {
        k.replace("_distribution", "")
        for k in cohort_summary.keys()
        if k.endswith("_distribution")
    }

    for seg_key in _STANDARD_SEGMENT_KEYS:
        # Is this segment covered?
        in_anchors = seg_key in anchor_overrides
        in_summary = seg_key in distribution_keys

        if not (in_anchors or in_summary):
            continue

        # Without Iris, we can't claim "calibrated" — best we can say is
        # "extrapolated" (we model it but haven't checked against ground truth
        # this run). Mark explicitly scoped dimensions as extrapolated; the
        # rest as novel if they appear in summary but weren't anchored.
        status: str = "extrapolated" if (in_anchors or in_summary) else "novel"

        segments.append(
            CoverageSegment(
                segment_name=seg_key,
                calibration_status=status,  # type: ignore[arg-type]
                confidence_delta=None,
            )
        )

    # If we found nothing at all, emit a single placeholder
    if not segments:
        segments.append(
            CoverageSegment(
                segment_name="all_segments",
                calibration_status="extrapolated",
                confidence_delta=None,
            )
        )

    return segments
