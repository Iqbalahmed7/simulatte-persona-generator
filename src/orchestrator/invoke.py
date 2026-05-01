"""
invoke_persona_generator() — the single public entry point for the orchestration layer.

This is the function any external caller (another Python project, a Claude agent,
a CI pipeline, a REST service) should use.  It:

  1.  Validates the brief
  2.  Advises on tier (or honours override)
  3.  Estimates cost and prints a formatted breakdown
  4.  Awaits confirmation (unless auto_confirm=True)
  5.  Runs the generation pipeline with quality enforcement
  6.  Optionally runs a simulation
  7.  Generates a pipeline documentation note
  8.  Returns a structured PersonaGenerationResult

Usage (async)::

    import asyncio
    from src.orchestrator import invoke_persona_generator
    from src.orchestrator.brief import PersonaGenerationBrief, RunIntent

    brief = PersonaGenerationBrief(
        client="LittleJoys",
        domain="cpg",
        business_problem="Why do Mumbai parents switch nutrition brands for under-5s?",
        count=50,
        run_intent=RunIntent.DELIVER,
        sarvam_enabled=True,
        anchor_overrides={"location": "Mumbai", "life_stage": "parent"},
        simulation=SimulationScenario(
            stimuli=[
                "Pediatrician-endorsed nutrition supplement for children aged 2-10",
                "Product packaging: Vitamin D + Iron, Indian pediatric certification",
                "Testimonial: Delhi mother says her son has more energy",
                "Price: Rs 649/month on Flipkart",
                "Limited offer: first month free on subscription",
            ],
            decision_scenario="Would you purchase a trial pack of this product today?",
        ),
        auto_confirm=False,  # Set True to skip the prompt
    )

    result = asyncio.run(invoke_persona_generator(brief))
    print(result.summary)
    result.save("./outputs/littlejoys-run.json")


Usage (sync wrapper)::

    from src.orchestrator import invoke_persona_generator_sync

    result = invoke_persona_generator_sync(brief)


Usage (HTTP via FastAPI extension)::

    POST /orchestrate
    Body: PersonaGenerationBrief JSON
    Returns: PersonaGenerationResult JSON
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.orchestrator.brief import PersonaGenerationBrief, RunIntent, SimulationScenario
from src.orchestrator.cost_estimator import CostEstimator
from src.orchestrator.pipeline_doc_writer import PipelineDocWriter
from src.orchestrator.result import CostActual, PersonaGenerationResult, QualityReport
from src.orchestrator.tier_advisor import TierAdvisor


# ── Internal imports from existing pipeline ───────────────────────────────────
# These are the existing entry points we wrap.
from src.cli import _run_generation, _run_simulation, _run_survey  # noqa: F401


async def invoke_persona_generator(
    brief: PersonaGenerationBrief,
    *,
    confirm_callback: Any | None = None,
) -> PersonaGenerationResult:
    """
    Async entry point.  Pass a PersonaGenerationBrief, get back a
    PersonaGenerationResult.

    Parameters
    ----------
    brief :
        The fully-specified PersonaGenerationBrief.
    confirm_callback :
        Optional async callable(estimate_str: str) -> bool that handles
        confirmation logic.  If None and brief.auto_confirm is False,
        uses stdin prompt.

    Returns
    -------
    PersonaGenerationResult
    """
    start_time = time.monotonic()
    run_id = f"pg-{brief.client.lower().replace(' ', '-')}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}-{uuid.uuid4().hex[:6]}"

    # ── 1. Tier advice ────────────────────────────────────────────────────
    advice = TierAdvisor.advise(brief)
    tier = advice.tier

    # ── 2. Cost estimate ──────────────────────────────────────────────────
    n_stimuli = len(brief.simulation.stimuli) if brief.simulation else 0
    has_decision = bool(brief.simulation and brief.simulation.decision_scenario) if brief.simulation else False

    estimator = CostEstimator(
        count=brief.count,
        tier=tier,
        n_stimuli=n_stimuli,
        has_decision_scenario=has_decision,
        has_corpus=bool(brief.domain_data),
    )
    estimate = estimator.compute()

    # ── 3. Pre-run confirmation ───────────────────────────────────────────
    if not brief.auto_confirm:
        alt_saving = None
        if advice.alt_tier and advice.alt_saving_pct:
            # Compute alt saving in dollars
            alt_est = CostEstimator(
                count=brief.count,
                tier=advice.alt_tier,
                n_stimuli=n_stimuli,
                has_decision_scenario=has_decision,
                has_corpus=bool(brief.domain_data),
            )
            alt_cost = alt_est.compute()
            alt_saving = estimate.total - alt_cost.total

        formatted = estimator.formatted_estimate(
            brief_label=f"{brief.client} / {brief.domain}",
            tier_recommendation_reason=advice.reason,
            alt_tier=advice.alt_tier,
            alt_saving=alt_saving,
        )
        print(formatted)
        print()

        if confirm_callback is not None:
            confirmed = await confirm_callback(formatted)
        else:
            confirmed = _stdin_confirm()

        if not confirmed:
            raise RuntimeError("Run cancelled by user at cost-estimate confirmation.")

    # ── 4. Resolve output directory ───────────────────────────────────────
    output_dir = Path(
        str(brief.output_dir)
        if brief.output_dir
        else os.getenv("COHORT_STORE_DIR", "/tmp/simulatte_cohorts")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 5. Generate personas ──────────────────────────────────────────────
    from src.persistence.streaming_writer import StreamingCohortWriter

    print(f"[orchestrator] Generating {brief.count} {tier.upper()} personas for {brief.client}…")

    # Determine cohort_id early so the streaming writer can use it as the
    # output filename (matches the single-file path set later).
    cohort_id_early = f"cohort-{brief.domain}-{run_id[-6:]}"

    streaming_writer: StreamingCohortWriter | None = None
    if StreamingCohortWriter.should_stream(brief.count):
        streaming_writer = StreamingCohortWriter(output_dir, cohort_id_early)
        # Begin the writer with the cohort-level metadata we already know;
        # cohort_summary will be added by finalize() after assemble_cohort().
        streaming_writer.begin({
            "cohort_id": cohort_id_early,
            "run_id": run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "domain": brief.domain,
            "client": brief.client,
            "business_problem": brief.business_problem or "",
            "tier": tier,
            "count_requested": brief.count,
        })
        print(
            f"[orchestrator] Streaming mode active — "
            f"threshold={StreamingCohortWriter.STREAMING_THRESHOLD}, "
            f"personas will be checkpointed as they complete."
        )

    raw_envelope = await _run_generation(
        count=brief.count,
        domain=brief.domain,
        mode=brief.mode,
        anchor_overrides=brief.anchor_overrides,
        persona_id_prefix=brief.persona_id_prefix,
        domain_data=brief.domain_data,
        sarvam_enabled=brief.sarvam_enabled,
        skip_gates=brief.skip_gates,
        registry_path=str(brief.registry_path) if brief.registry_path else None,
        client=brief.client,
        streaming_writer=streaming_writer,
        max_attempts=brief.max_retries_per_persona,
    )

    # Handle Sarvam wrapper
    if isinstance(raw_envelope, dict) and "envelope" in raw_envelope:
        cohort_envelope = raw_envelope["envelope"]
    else:
        cohort_envelope = raw_envelope

    # ── 6. Save cohort to disk ────────────────────────────────────────────
    if streaming_writer is not None:
        # Streaming writer already wrote the file to output_dir / cohort_id_early.json.
        # Use cohort_id_early as the authoritative cohort_id so that the simulation
        # step below can find the file.  (The envelope's internal cohort_id may differ
        # from the filename that the streaming writer committed.)
        cohort_id = cohort_id_early
        cohort_file_path = output_dir / f"{cohort_id_early}.json"
        streaming_writer.finalize(
            envelope_meta=cohort_envelope,  # full dict including stratified personas
            overwrite=True,
        )
        print(f"[orchestrator] Cohort streamed → {cohort_file_path}")
    else:
        # Original single-write path (small cohorts below threshold)
        cohort_id = cohort_envelope.get("cohort_id", cohort_id_early)
        cohort_file_path = output_dir / f"{cohort_id}.json"
        cohort_file_path.write_text(json.dumps(cohort_envelope, default=str, indent=2))
        print(f"[orchestrator] Cohort saved → {cohort_file_path}")

    # ── 7. Quality enforcement ─────────────────────────────────────────────
    quality_report = _build_quality_report(cohort_envelope)

    # Check quarantine threshold
    total_personas = len(cohort_envelope.get("personas", []))
    if total_personas > 0:
        qpct = quality_report.personas_quarantined / total_personas
        if qpct > brief.max_quarantine_pct:
            raise RuntimeError(
                f"Quality enforcement failed: {quality_report.personas_quarantined}/{total_personas} "
                f"personas quarantined ({qpct:.0%} > threshold {brief.max_quarantine_pct:.0%}). "
                f"Check domain data quality or relax max_quarantine_pct."
            )

    # ── 7b. PQS — internal quality tracking ────────────────────────────────
    pqs_score: float | None = None
    try:
        from src.quality.pqs import compute_pqs_from_dict, format_pqs_summary
        pqs_report = compute_pqs_from_dict(cohort_envelope)
        if pqs_report is not None:
            pqs_score = pqs_report["pqs"]
            print(format_pqs_summary(pqs_report))
            # Persist PQS in the cohort envelope for historical tracking
            cohort_envelope["_pqs"] = pqs_report
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug("PQS computation skipped: %s", e)

    # ── 8. Optional simulation ────────────────────────────────────────────
    simulation_results: dict | None = None
    sim_cost = 0.0

    if brief.simulation and brief.simulation.stimuli:
        print(f"[orchestrator] Running {tier.upper()} simulation ({len(brief.simulation.stimuli)} stimuli)…")

        scenario_data = {
            "stimuli": brief.simulation.stimuli,
            "decision_scenario": brief.simulation.decision_scenario,
        }

        simulation_results = await _run_simulation(
            cohort_path=str(cohort_file_path),
            scenario_data=scenario_data,
            rounds=brief.simulation.rounds,
            tier=tier,
            social_level=brief.simulation.social_level,
            social_topology=brief.simulation.social_topology,
        )
        print("[orchestrator] Simulation complete.")

        # Rough sim cost from estimator
        sim_cost = estimate.sim_total

    # ── 9 / 10. Extract personas then compute actual costs ────────────────
    personas = cohort_envelope.get("personas", [])

    cost_actual = CostActual(
        pre_generation=estimate.pre_gen_total,
        generation=estimate.gen_total,
        simulation=sim_cost,
        count=len(personas),
    )

    # ── 10. Build result ──────────────────────────────────────────────────
    wall_clock = time.monotonic() - start_time

    result = PersonaGenerationResult(
        run_id=run_id,
        cohort_id=cohort_id,
        client=brief.client,
        domain=brief.domain,
        tier_used=tier,
        count_requested=brief.count,
        count_delivered=len(personas),
        cost_actual=cost_actual,
        quality_report=quality_report,
        personas=personas,
        cohort_envelope=cohort_envelope,
        simulation_results=simulation_results,
        cohort_file_path=str(cohort_file_path),
        generated_at=datetime.now(timezone.utc),
        wall_clock_seconds=wall_clock,
    )

    # ── 11. Calibration Card (Spec 02) ───────────────────────────────────
    # Non-optional: every deliverable ships with a card. If Iris has no
    # benchmark data, the card emits as "uncalibrated" with an honest reason.
    # iris_outputs=None is the correct call here — Iris integration is a
    # future step once Iris exposes a run-time API. For now the card always
    # emits; the study team can back-fill iris_outputs via build_calibration_card
    # once Iris outputs are available.
    try:
        from src.calibration.card_builder import build_calibration_card
        result.calibration_card = build_calibration_card(
            study_id=run_id,
            cohort_envelope=cohort_envelope,
            iris_outputs=None,  # TODO: wire Iris run outputs here
        )
        print(
            f"[orchestrator] Calibration card → "
            f"status={result.calibration_card.calibration_status}"
        )
    except Exception as _cc_err:
        import logging as _log
        _log.getLogger(__name__).warning(
            "build_calibration_card failed (%s); result.calibration_card will be None.",
            _cc_err,
        )

    # ── 12. Pipeline documentation ────────────────────────────────────────
    if brief.emit_pipeline_doc:
        doc_dir = output_dir / "pipeline_docs"
        writer = PipelineDocWriter(result, brief, estimate)
        doc_path = writer.write(output_dir=doc_dir)
        result.pipeline_doc_path = str(doc_path)
        print(f"[orchestrator] Pipeline doc → {doc_path}")

    print(f"[orchestrator] Done. {result.summary}")
    return result


def invoke_persona_generator_sync(
    brief: PersonaGenerationBrief,
    **kwargs: Any,
) -> PersonaGenerationResult:
    """
    Synchronous wrapper around invoke_persona_generator().

    Use this when you cannot run an async event loop directly
    (e.g. inside a Jupyter notebook cell, a Flask view, etc.).
    """
    return asyncio.run(invoke_persona_generator(brief, **kwargs))


# ── Private helpers ────────────────────────────────────────────────────────────

def _stdin_confirm() -> bool:
    """Simple stdin confirmation prompt."""
    try:
        ans = input("Proceed? [y/n] → ").strip().lower()
        return ans in ("y", "yes", "")
    except (EOFError, KeyboardInterrupt):
        return False


def _build_quality_report(cohort_envelope: dict) -> QualityReport:
    """
    Build a QualityReport from a CohortEnvelope dict.

    Consumes the canonical ``gate_results`` list written by assemble_cohort
    (each entry is a ValidationResult.to_dict()).  Gate IDs map 1:1 with the
    CohortGateRunner protocol (G6, G7, G8, G9, G11); no pass/fail state is
    inferred from secondary fields such as cohort_summary or calibration_state.

    Two non-protocol signals are appended independently:
    - ``Grounding-AnchoredTendencies``: cohort tendency anchoring signal.
    - ``Persona-AttributePresence``: quarantine marker for attribute-empty personas.
    """
    gates_passed: list[str] = []
    gates_failed: list[str] = []
    gate_statuses: list[dict[str, Any]] = []

    # Protocol gate ID → human-readable report label (1:1 mapping).
    _GATE_LABELS: dict[str, str] = {
        "G1": "G1-SchemaValidity",
        "G2": "G2-HardConstraints",
        "G3": "G3-TendencyAttributeConsistency",
        "G4": "G4-NarrativeCompleteness",
        "G5": "G5-NarrativeAlignment",
        "G6": "G6-Diversity",
        "G7": "G7-Distinctiveness",
        "G8": "G8-TypeCoverage",
        "G9": "G9-TensionCompleteness",
        "G10": "G10-MemoryBootstrap",
        "G11": "G11-TendencySource",
        "G12": "G12-SimulationGrounding",
    }

    canonical_gate_results = {
        gr.get("gate"): gr for gr in cohort_envelope.get("gate_results", [])
    }
    personas = cohort_envelope.get("personas", [])
    personas_validated_count = len(personas)

    def _append_status(
        gate_id: str,
        status: str,
        reason: str | None = None,
        failures: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        label = _GATE_LABELS[gate_id]
        payload: dict[str, Any] = {
            "gate_id": gate_id,
            "label": label,
            "status": status,  # enum: passed | failed | not_run
        }
        if reason is not None:
            payload["reason"] = reason
        if failures:
            payload["failures"] = failures
        if extra:
            payload.update(extra)
        gate_statuses.append(payload)
        if status == "passed":
            gates_passed.append(label)
        elif status == "failed":
            gates_failed.append(label)

    # G1-G5 run at generation stage, not cohort orchestrator stage.
    for gid in ("G1", "G2", "G3", "G4", "G5"):
        _append_status(
            gid,
            "not_run",
            reason="deferred_to_generation_stage",
            extra={"personas_validated_count": personas_validated_count},
        )

    # G6, G7, G8, G9, G11 from canonical cohort validator output.
    for gid in ("G6", "G7", "G8", "G9", "G11"):
        gr = canonical_gate_results.get(gid)
        if gr is None:
            _append_status(
                gid,
                "not_run",
                reason="deferred_to_generation_stage",
                extra={"personas_validated_count": personas_validated_count},
            )
            continue
        if gr.get("passed"):
            _append_status(gid, "passed")
        else:
            _append_status(gid, "failed", failures=gr.get("failures", []))

    # G10 mode-aware status at orchestrator stage.
    mode = str(cohort_envelope.get("mode", "quick"))
    if mode != "simulation-ready":
        _append_status("G10", "not_run", reason="not_applicable_mode_quick")
    else:
        weak_seed_ids: list[str] = []
        for p in personas:
            pid = p.get("persona_id", "unknown")
            observations = (
                p.get("memory", {})
                .get("working", {})
                .get("observations", [])
            )
            if len(observations) < 3:
                weak_seed_ids.append(pid)
        if weak_seed_ids:
            _append_status(
                "G10",
                "failed",
                failures=[
                    f"seed memory observations <3 for persona_ids={weak_seed_ids}"
                ],
            )
        else:
            _append_status("G10", "passed", reason="validated_at_generation_stage")

    # Grounding tendency anchoring signal (not a CohortGateRunner gate).
    grounding = cohort_envelope.get("grounding_summary", {})
    grounding_state = "ungrounded"
    if grounding.get("tendency_source_distribution"):
        anchored_pct = grounding["tendency_source_distribution"].get("grounded", 0)
        if anchored_pct > 0:
            grounding_state = "anchored"
            gates_passed.append("Grounding-AnchoredTendencies")

    # Per-persona attribute presence check — quarantine marker only; not a protocol gate.
    quarantined = 0
    for persona in personas:
        if not persona.get("attributes", {}):
            quarantined += 1

    if quarantined > 0:
        gates_failed.append("Persona-AttributePresence")

    # G12 runs post-simulation contamination check, not at cohort stage.
    _append_status("G12", "not_run", reason="deferred_to_simulation_stage")

    # Distinctiveness score for downstream reporting (informational, not a gate input).
    cs = cohort_envelope.get("cohort_summary", {})
    dist_score = cs.get("distinctiveness_score")

    report = QualityReport(
        gates_passed=gates_passed,
        gates_failed=gates_failed,
        personas_quarantined=quarantined,
        personas_regenerated=0,
        distinctiveness_score=dist_score,
        grounding_state=grounding_state,
    )
    # Attach canonical per-gate status payload without requiring QualityReport schema changes.
    report.gate_statuses = gate_statuses  # type: ignore[attr-defined]
    return report
