"""src/onboarding/onboarding_workflow.py

7-step onboarding orchestrator for the Simulatte Persona Engine.

Sprint 28 — No LLM calls in this module itself.  All collaborator modules
(ingestion, gates, cluster_pipeline, feature_builder) are imported lazily
inside run_onboarding() to avoid circular-import issues while the sprint is
still in progress.

Steps
-----
1. Parse ICP spec         → ICPSpec (+ collision detection)
2. Select domain template → top TemplateMatch
3. Ingest data            → IngestionResult  (skip if data_bytes is None)
4. G-O1 gate              → ≥ 200 valid signals  (skip if step 3 skipped)
5. Build feature vectors  → BehaviouralFeatures  (skip if step 3 skipped)
6. G-O2 gate              → cluster silhouette stability  (skip if step 5 skipped)
7. Report OnboardingResult

Status rules
------------
- "complete": steps 1–6 all ok (or appropriately skipped)
- "partial":  any gate failure (G-O1 or G-O2) — workflow continues to report
- "failed":   step 1 or step 2 raises — can't proceed without ICP or template
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from src.onboarding.feature_builder import BehaviouralFeatures


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass
class StepLog:
    step: int
    name: str
    status: Literal["ok", "failed", "skipped"]
    detail: str = ""


@dataclass
class OnboardingResult:
    status: Literal["complete", "partial", "failed"]
    icp_spec: Any                   # ICPSpec object
    template_match: Any | None      # TemplateMatch (top match)
    ingestion_result: Any | None    # IngestionResult
    features: Any | None            # BehaviouralFeatures
    cluster_result: Any | None      # ClusterResult
    step_log: list[StepLog]         # One entry per step
    notes: str


# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------


def _features_to_vectors(features: "BehaviouralFeatures") -> list[list[float]]:
    """Flatten BehaviouralFeatures into a list of feature vectors.

    Produces a single aggregate vector from all scalar/dict fields and
    replicates it so the cluster pipeline has enough samples to fit a GMM.
    In Sprint 29+ this will be replaced by per-persona signal aggregation.
    """
    vec: list[float] = [
        features.price_salience_index,
        *features.trust_source_distribution.values(),
        *features.switching_trigger_distribution.values(),
        *features.objection_cluster_frequencies.values(),
        *features.purchase_trigger_distribution.values(),
    ]
    # Return at least 10 copies so the cluster pipeline has enough samples.
    return [vec] * max(10, features.n_signals)


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


def run_onboarding(
    icp_json: dict,
    data_bytes: bytes | None = None,
    run_tagger: bool = False,
    llm_client: Any = None,
) -> OnboardingResult:
    """Run the 7-step onboarding pipeline.

    Parameters
    ----------
    icp_json:
        Raw ICP spec dict (will be JSON-serialised and passed to
        parse_icp_spec so that synonym resolution and validation are applied).
    data_bytes:
        Raw client data bytes.  Pass None when no data has been provided;
        steps 3–6 will be skipped gracefully.
    run_tagger:
        When True and llm_client is supplied, step 3 will request signal
        tagging.  The orchestrator itself makes no LLM calls.
    llm_client:
        Opaque LLM client forwarded verbatim to ingest().

    Returns
    -------
    OnboardingResult
        Never raises — exceptions are caught per step and recorded in
        step_log with status "failed".
    """
    log: list[StepLog] = []
    overall_status: Literal["complete", "partial", "failed"] = "complete"
    notes_parts: list[str] = []

    # Mutable state accumulated across steps
    spec: Any = None
    top: Any = None
    ingestion_result: Any = None
    features: Any = None
    cluster_result: Any = None

    # ------------------------------------------------------------------
    # Step 1 — Parse ICP spec
    # ------------------------------------------------------------------
    try:
        from src.taxonomy.icp_spec_parser import parse_icp_spec

        spec = parse_icp_spec(icp_json)
        log.append(StepLog(1, "parse_icp_spec", "ok"))
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        log.append(StepLog(1, "parse_icp_spec", "failed", detail=detail))
        notes_parts.append(f"Step 1 failed — {detail}")
        overall_status = "failed"
        # Cannot proceed without a valid ICP spec
        return OnboardingResult(
            status=overall_status,
            icp_spec=None,
            template_match=None,
            ingestion_result=None,
            features=None,
            cluster_result=None,
            step_log=log,
            notes="; ".join(notes_parts),
        )

    # ------------------------------------------------------------------
    # Step 2 — Select domain template
    # ------------------------------------------------------------------
    try:
        from src.taxonomy.template_selector import LOW_CONFIDENCE_THRESHOLD, select_template

        matches = select_template(spec)
        top = matches[0] if matches else None

        if top is not None:
            detail = f"top={top.template_name} conf={top.confidence:.2f}"
            if top.confidence < LOW_CONFIDENCE_THRESHOLD:
                notes_parts.append(
                    f"Low template confidence ({top.confidence:.2f}); "
                    "consider clarifying the domain."
                )
        else:
            detail = "no matches returned"
            notes_parts.append("Template selector returned no matches.")

        log.append(StepLog(2, "select_template", "ok", detail=detail))
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        log.append(StepLog(2, "select_template", "failed", detail=detail))
        notes_parts.append(f"Step 2 failed — {detail}")
        overall_status = "failed"
        # Cannot proceed without a template
        return OnboardingResult(
            status=overall_status,
            icp_spec=spec,
            template_match=None,
            ingestion_result=None,
            features=None,
            cluster_result=None,
            step_log=log,
            notes="; ".join(notes_parts),
        )

    # ------------------------------------------------------------------
    # Step 3 — Ingest data
    # ------------------------------------------------------------------
    if data_bytes is None:
        log.append(StepLog(3, "ingest_data", "skipped"))
    else:
        try:
            from src.onboarding.ingestion import ingest

            ingestion_result = ingest(
                data_bytes,
                run_tagger=run_tagger,
                llm_client=llm_client,
            )
            log.append(
                StepLog(
                    3,
                    "ingest_data",
                    "ok",
                    detail=f"format={ingestion_result.format_detected}",
                )
            )
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            log.append(StepLog(3, "ingest_data", "failed", detail=detail))
            notes_parts.append(f"Step 3 failed — {detail}")
            overall_status = "partial"
            # Steps 4–6 cannot run without ingestion; fall through to report
            _pad_skipped_steps(log, from_step=4, to_step=6)
            return OnboardingResult(
                status=overall_status,
                icp_spec=spec,
                template_match=top,
                ingestion_result=None,
                features=None,
                cluster_result=None,
                step_log=log,
                notes="; ".join(notes_parts),
            )

    # ------------------------------------------------------------------
    # Step 4 — G-O1 gate (≥ 200 valid signals)
    # ------------------------------------------------------------------
    go1_passed: bool = True  # vacuously true when ingestion was skipped

    if ingestion_result is None:
        log.append(StepLog(4, "g_o1_gate", "skipped"))
    else:
        try:
            from src.validation.onboarding_gates import check_go1

            go1 = check_go1(ingestion_result)
            gate_status: Literal["ok", "failed", "skipped"] = (
                "ok" if go1.passed else "failed"
            )
            log.append(StepLog(4, "g_o1_gate", gate_status, detail=go1.detail))
            if not go1.passed:
                go1_passed = False
                overall_status = "partial"
                notes_parts.append(f"G-O1 gate failed — {go1.detail}")
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            log.append(StepLog(4, "g_o1_gate", "failed", detail=detail))
            notes_parts.append(f"Step 4 error — {detail}")
            go1_passed = False
            overall_status = "partial"

    # ------------------------------------------------------------------
    # Step 5 — Build feature vectors
    # ------------------------------------------------------------------
    if ingestion_result is None or not ingestion_result.ready_for_grounding:
        reason = (
            "no ingestion result"
            if ingestion_result is None
            else "ingestion not ready for grounding"
        )
        log.append(StepLog(5, "build_features", "skipped", detail=reason))
    else:
        try:
            from src.onboarding.feature_builder import build_features_from_tagged_corpus

            corpus = ingestion_result.tagged_corpus
            if corpus is not None:
                features = build_features_from_tagged_corpus(corpus, spec)
                log.append(StepLog(5, "build_features", "ok"))
            else:
                log.append(
                    StepLog(5, "build_features", "skipped", detail="no tagged corpus")
                )
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            log.append(StepLog(5, "build_features", "failed", detail=detail))
            notes_parts.append(f"Step 5 failed — {detail}")
            overall_status = "partial"

    # ------------------------------------------------------------------
    # Step 6 — G-O2 gate + clustering
    # ------------------------------------------------------------------
    if features is None:
        log.append(StepLog(6, "g_o2_gate", "skipped", detail="no feature vectors"))
    else:
        try:
            from src.onboarding.cluster_pipeline import run_cluster_pipeline
            from src.validation.onboarding_gates import check_go2

            feature_vectors = _features_to_vectors(features)
            cluster_result = run_cluster_pipeline(feature_vectors)
            go2 = check_go2(cluster_result)
            gate_status = "ok" if go2.passed else "failed"
            log.append(StepLog(6, "g_o2_gate", gate_status, detail=go2.detail))
            if not go2.passed:
                overall_status = "partial"
                notes_parts.append(f"G-O2 gate failed — {go2.detail}")
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            log.append(StepLog(6, "g_o2_gate", "failed", detail=detail))
            notes_parts.append(f"Step 6 error — {detail}")
            overall_status = "partial"

    # ------------------------------------------------------------------
    # Step 7 — Report
    # ------------------------------------------------------------------
    return OnboardingResult(
        status=overall_status,
        icp_spec=spec,
        template_match=top,
        ingestion_result=ingestion_result,
        features=features,
        cluster_result=cluster_result,
        step_log=log,
        notes="; ".join(notes_parts) if notes_parts else "ok",
    )


# ---------------------------------------------------------------------------
# Internal utility
# ---------------------------------------------------------------------------


def _pad_skipped_steps(
    log: list[StepLog],
    from_step: int,
    to_step: int,
) -> None:
    """Append skipped StepLog entries for a range of steps.

    Used when an early failure means downstream steps cannot run and we
    still want the log to contain one entry per step for consumers that
    iterate over step_log by index.
    """
    _STEP_NAMES: dict[int, str] = {
        4: "g_o1_gate",
        5: "build_features",
        6: "g_o2_gate",
    }
    for step_num in range(from_step, to_step + 1):
        name = _STEP_NAMES.get(step_num, f"step_{step_num}")
        log.append(StepLog(step_num, name, "skipped", detail="upstream step failed"))
