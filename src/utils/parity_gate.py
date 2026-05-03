"""parity_gate.py — calibration parity gate for multi-provider routing.

Before a flexible stage is allowed to use a new provider (e.g. OpenAI), it must
pass a parity check: run a fixed eval set through both Anthropic (baseline)
and the candidate provider, then measure whether their outputs are statistically
equivalent on the metrics that matter for that stage.

Usage:
    from src.utils.parity_gate import run_parity_check

    result = await run_parity_check(
        stage="signal_tag",
        baseline=anthropic_client,
        candidate=openai_client,
        eval_set=load_calibration_set("signal_tag"),
    )
    if result.passed:
        # Update PROVIDER_LOCKS["signal_tag"]["calibrated_for"] to include "openai"
        ...

Eval sets live in `calibration/parity/{stage}.jsonl` — list of {prompt, system}
records. Build them once per stage from real production traffic.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.sarvam.llm_client import BaseLLMClient


# ── Per-stage parity thresholds ────────────────────────────────────────────
# How close candidate output must be to baseline to pass the gate.

PARITY_THRESHOLDS: dict[str, dict[str, float]] = {
    "signal_tag":     {"jaccard_min": 0.75, "schema_match_min": 1.0},
    "domain_extract": {"jaccard_min": 0.70, "schema_match_min": 1.0},
    "summarise":      {"semantic_sim_min": 0.78, "length_ratio_max": 1.4},
    "reflect":        {"semantic_sim_min": 0.80, "tone_drift_max": 0.15},
    "perceive":       {"semantic_sim_min": 0.82, "framing_drift_max": 0.15},
    "frame_score":    {"bucket_match_min": 0.85, "score_mae_max": 1.0},
    # high-sensitivity stages don't have parity thresholds — they cannot swap
}


@dataclass
class ParityResult:
    """Result of running a parity check between baseline and candidate."""
    stage: str
    baseline_provider: str
    candidate_provider: str
    n_samples: int
    metrics: dict[str, float] = field(default_factory=dict)
    threshold: dict[str, float] = field(default_factory=dict)
    passed: bool = False
    failures: list[str] = field(default_factory=list)
    notes: str = ""

    def summary(self) -> str:
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        lines = [
            f"{status} parity check: {self.stage}",
            f"  baseline:  {self.baseline_provider}",
            f"  candidate: {self.candidate_provider}",
            f"  samples:   {self.n_samples}",
        ]
        for k, v in self.metrics.items():
            t = self.threshold.get(k, "—")
            lines.append(f"    {k}: {v:.3f} (threshold: {t})")
        if self.failures:
            lines.append("  failures:")
            lines.extend(f"    - {f}" for f in self.failures)
        return "\n".join(lines)


def load_eval_set(stage: str, base_dir: Path | None = None) -> list[dict]:
    """Load calibration eval set for a stage. Returns list of {system, messages}."""
    base = base_dir or Path("calibration/parity")
    path = base / f"{stage}.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"No eval set for stage '{stage}' at {path}. "
            f"Build one from production traffic before running parity."
        )
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


async def run_parity_check(
    *,
    stage: str,
    baseline: BaseLLMClient,
    candidate: BaseLLMClient,
    eval_set: list[dict],
    judge_client: Any | None = None,
) -> ParityResult:
    """Run baseline vs candidate on eval_set, score parity.

    The actual metric computation is stage-specific and stubbed here — wire
    each stage's scorer in `src/calibration/parity_scorers/`. This function
    is the orchestrator only.
    """
    if stage not in PARITY_THRESHOLDS:
        return ParityResult(
            stage=stage,
            baseline_provider=baseline.provider,
            candidate_provider=candidate.provider,
            n_samples=0,
            passed=False,
            notes=(f"Stage '{stage}' is high-sensitivity or unregistered. "
                   f"No parity gate available — stage cannot use multi-provider."),
        )

    # Run both providers across the eval set
    baseline_outs: list[str] = []
    candidate_outs: list[str] = []
    for record in eval_set:
        sys = record.get("system", "")
        msgs = record.get("messages", [])
        max_tok = record.get("max_tokens", 1024)
        baseline_outs.append(await baseline.complete(
            system=sys, messages=msgs, max_tokens=max_tok
        ))
        candidate_outs.append(await candidate.complete(
            system=sys, messages=msgs, max_tokens=max_tok
        ))

    # Stage-specific scorer (stub — implement per stage)
    metrics = await _score_stage(
        stage=stage,
        baseline_outs=baseline_outs,
        candidate_outs=candidate_outs,
        eval_set=eval_set,
        judge_client=judge_client,
    )

    # Compare against thresholds
    thresholds = PARITY_THRESHOLDS[stage]
    failures: list[str] = []
    for metric, threshold_value in thresholds.items():
        actual = metrics.get(metric)
        if actual is None:
            failures.append(f"missing metric: {metric}")
            continue
        # min thresholds: actual must be >=, max thresholds: actual must be <=
        if metric.endswith("_min") and actual < threshold_value:
            failures.append(f"{metric}: {actual:.3f} < {threshold_value}")
        elif metric.endswith("_max") and actual > threshold_value:
            failures.append(f"{metric}: {actual:.3f} > {threshold_value}")

    return ParityResult(
        stage=stage,
        baseline_provider=baseline.provider,
        candidate_provider=candidate.provider,
        n_samples=len(eval_set),
        metrics=metrics,
        threshold=thresholds,
        passed=(len(failures) == 0),
        failures=failures,
    )


async def _score_stage(
    *,
    stage: str,
    baseline_outs: list[str],
    candidate_outs: list[str],
    eval_set: list[dict],
    judge_client: Any | None,
) -> dict[str, float]:
    """Stage-specific scoring. STUB — implement per stage in calibration/parity_scorers/.

    Returns the metric dict matching PARITY_THRESHOLDS[stage] keys.
    """
    # TODO(parity): implement stage scorers. For now return empty so the gate
    # fails closed (no swap permitted until scorers are wired).
    return {}
