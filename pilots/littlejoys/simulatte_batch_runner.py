"""pilots/littlejoys/simulatte_batch_runner.py

Simulatte-backed batch runner for LittleJoys journeys.

Drop-in replacement for src.simulation.batch_runner.run_batch that routes
JourneyConfig stimuli through the Simulatte cognitive loop (run_loop) with
tier support.

Public API:
  run_simulatte_batch(personas, journey_config, tier="signal") -> dict
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from src.cognition.loop import run_loop
from src.experiment.session import SimulationTier

if TYPE_CHECKING:
    from src.schema.persona import PersonaRecord
    from src.simulation.journey_config import JourneyConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier mapping — exposed so callers can pass string tier names
# ---------------------------------------------------------------------------

TIER_MAP: dict[str, SimulationTier] = {
    "deep": SimulationTier.DEEP,
    "signal": SimulationTier.SIGNAL,
    "volume": SimulationTier.VOLUME,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _decision_output_to_dict(decision_output: Any) -> dict:
    """Serialise a DecisionOutput dataclass to a plain dict."""
    if decision_output is None:
        return {}
    return {
        "decision": getattr(decision_output, "decision", "unknown"),
        "confidence": getattr(decision_output, "confidence", 0),
        "reasoning_trace": getattr(decision_output, "reasoning_trace", ""),
        "gut_reaction": getattr(decision_output, "gut_reaction", ""),
        "key_drivers": list(getattr(decision_output, "key_drivers", [])),
        "objections": list(getattr(decision_output, "objections", [])),
        "what_would_change_mind": getattr(decision_output, "what_would_change_mind", ""),
        "noise_applied": getattr(decision_output, "noise_applied", 0),
        "follow_up_action": getattr(decision_output, "follow_up_action", ""),
        "implied_purchase": bool(getattr(decision_output, "implied_purchase", False)),
    }


def _build_decision_scenario_map(journey_config: "JourneyConfig") -> dict[int, str]:
    """Map each decision tick to its description string for run_loop."""
    return {d.tick: d.description for d in journey_config.decisions}


async def _run_one_persona(
    persona: "PersonaRecord",
    journey_config: "JourneyConfig",
    tier: SimulationTier,
) -> dict:
    """Run a single persona through every stimulus in the journey.

    Returns a log dict compatible with the LittleJoys app's Results tab.
    The snapshots list records one entry per stimulus tick, and each entry
    that coincides with a decision tick embeds the full DecisionOutput dict
    under ``decision_result``.
    """
    decision_scenario_map = _build_decision_scenario_map(journey_config)
    snapshots: list[dict] = []
    final_decision: dict | None = None
    reordered = False
    current_persona = persona

    # Iterate stimuli in tick order so working memory builds naturally
    stimuli_sorted = sorted(journey_config.stimuli, key=lambda s: s.tick)

    _PURCHASE_DECISIONS = {"buy", "trial", "reorder"}

    for stimulus_cfg in stimuli_sorted:
        tick = stimulus_cfg.tick
        stimulus_text = stimulus_cfg.content
        stimulus_id = stimulus_cfg.id
        decision_scenario = decision_scenario_map.get(tick)

        updated_persona, loop_result = await run_loop(
            stimulus=stimulus_text,
            persona=current_persona,
            stimulus_id=stimulus_id,
            decision_scenario=decision_scenario,
            tier=tier,
        )
        current_persona = updated_persona

        # Build a snapshot for this tick
        snapshot: dict[str, Any] = {
            "tick": tick,
            "stimulus_id": stimulus_id,
            "stimulus_type": stimulus_cfg.type,
            "observation_content": loop_result.observation.content,
            "observation_importance": loop_result.observation.importance,
            "reflected": loop_result.reflected,
            "memories_count": (
                len(updated_persona.memory.working.observations)
                + len(updated_persona.memory.working.reflections)
            ),
            # brand_trust: best-effort float from simulation_state awareness_set
            "brand_trust": _extract_brand_trust(
                updated_persona, journey_config.primary_brand
            ),
            "decision_result": None,
        }

        if loop_result.decided and loop_result.decision is not None:
            decision_dict = _decision_output_to_dict(loop_result.decision)
            snapshot["decision_result"] = decision_dict
            final_decision = decision_dict

            # Determine reorder flag: second purchase-like event counts as reorder.
            # A purchase event is either:
            #   (a) decision label in _PURCHASE_DECISIONS, or
            #   (b) implied_purchase=True — decision was research_more/defer but
            #       follow_up_action describes an actual buy/order commitment.
            decision_label = decision_dict.get("decision", "").lower()
            is_purchase = (
                decision_label in _PURCHASE_DECISIONS
                or decision_dict.get("implied_purchase", False)
            )
            if is_purchase:
                # Scan prior snapshots for any earlier purchase event (explicit or implied)
                already_bought = any(
                    (s.get("decision_result") or {}).get("decision", "").lower()
                    in _PURCHASE_DECISIONS
                    or (s.get("decision_result") or {}).get("implied_purchase", False)
                    for s in snapshots
                )
                if already_bought:
                    reordered = True

        snapshots.append(snapshot)

    # Derive trust_by_tick for the aggregate (brand trust over time)
    trust_by_tick = _build_trust_by_tick(snapshots, journey_config.primary_brand)

    return {
        "persona_id": persona.persona_id,
        "display_name": persona.narrative.display_name,
        "journey_id": journey_config.journey_id,
        "snapshots": snapshots,
        "final_decision": final_decision,
        "reordered": reordered,
        "trust_by_tick": trust_by_tick,
    }


def _extract_brand_trust(persona: "PersonaRecord", primary_brand: str) -> dict[str, float]:
    """Return a brand -> trust dict from awareness_set, falling back to empty."""
    awareness = persona.memory.working.simulation_state.awareness_set
    if not awareness:
        return {}
    result: dict[str, float] = {}
    for brand, info in awareness.items():
        if isinstance(info, dict):
            trust_val = info.get("trust", info.get("trust_level", None))
            if trust_val is not None:
                try:
                    result[brand] = float(trust_val)
                except (TypeError, ValueError):
                    pass
        elif isinstance(info, (int, float)):
            result[brand] = float(info)
    return result


def _build_trust_by_tick(snapshots: list[dict], primary_brand: str) -> dict[int, float]:
    """Extract primary-brand trust at each tick from snapshots."""
    trust_by_tick: dict[int, float] = {}
    for snap in snapshots:
        brand_trust = snap.get("brand_trust", {}) or {}
        tick = snap.get("tick")
        if tick is None:
            continue
        if primary_brand in brand_trust:
            trust_by_tick[tick] = brand_trust[primary_brand]
        elif brand_trust:
            # Fall back to max trust value across any brand
            trust_by_tick[tick] = max(brand_trust.values())
    return trust_by_tick


def _build_error_log(
    persona: "PersonaRecord",
    journey_config: "JourneyConfig",
    exc: Exception,
) -> dict:
    """Build a minimal error log entry for a persona that failed."""
    return {
        "persona_id": persona.persona_id,
        "display_name": persona.narrative.display_name,
        "journey_id": journey_config.journey_id,
        "error": str(exc),
        "snapshots": [],
        "final_decision": None,
        "reordered": False,
        "trust_by_tick": {},
    }


# ---------------------------------------------------------------------------
# Aggregate builder
# ---------------------------------------------------------------------------


def _build_aggregate(
    logs: list[dict],
    journey_id: str,
) -> dict:
    """
    Build an aggregate dict matching JourneyAggregate.to_dict() schema so the
    LittleJoys app's _render_results_panel reads correctly.

    Rather than reimplementing all the logic, we delegate to LJ's own
    aggregate_journeys when the import is available (preferred path).
    Falls back to a minimal hand-rolled aggregate when LJ is not on sys.path.
    """
    try:
        # Preferred: use LittleJoys aggregate_journeys for full fidelity
        import sys
        import os
        lj_src = os.path.join(
            os.path.dirname(__file__),  # pilots/littlejoys/
            "..", "..", "..", "1. LittleJoys",  # project root of LJ
        )
        lj_src = os.path.normpath(lj_src)
        if lj_src not in sys.path:
            sys.path.insert(0, lj_src)

        from src.simulation.journey_result import aggregate_journeys  # type: ignore[import]
        agg = aggregate_journeys(logs)
        return agg.to_dict()

    except Exception as import_err:  # noqa: BLE001
        logger.warning(
            "_build_aggregate(): could not import LJ aggregate_journeys (%s) — "
            "using minimal fallback aggregate",
            import_err,
        )
        return _minimal_aggregate(logs, journey_id)


def _minimal_aggregate(logs: list[dict], journey_id: str) -> dict:
    """Minimal aggregate for when LJ's journey_result is unavailable."""
    from collections import Counter

    errors = sum(1 for lg in logs if lg.get("error"))
    valid = [lg for lg in logs if not lg.get("error")]

    first_decisions: Counter[str] = Counter()
    second_decisions: Counter[str] = Counter()
    first_drivers: Counter[str] = Counter()
    second_drivers: Counter[str] = Counter()
    first_objections: Counter[str] = Counter()
    second_objections: Counter[str] = Counter()

    _PURCHASE_DECISIONS = {"buy", "trial", "reorder"}
    reorderers = 0
    first_buyers = 0

    trust_by_tick: dict[int, list[float]] = {}

    for lg in valid:
        snaps = lg.get("snapshots", []) or []
        dec_snaps = [
            s for s in snaps
            if s.get("decision_result") and isinstance(s.get("decision_result"), dict)
            and "error" not in s["decision_result"]
        ]
        dec_snaps.sort(key=lambda s: s.get("tick", 0))

        first_dr = dec_snaps[0]["decision_result"] if dec_snaps else {}
        second_dr = dec_snaps[-1]["decision_result"] if len(dec_snaps) > 1 else {}

        first_label = str(first_dr.get("decision", "unknown")).lower()
        second_label = str(second_dr.get("decision", "unknown")).lower() if second_dr else "unknown"

        first_decisions[first_label] += 1
        if second_dr:
            second_decisions[second_label] += 1

        for d in (first_dr.get("key_drivers") or []):
            first_drivers[str(d)] += 1
        for o in (first_dr.get("objections") or []):
            first_objections[str(o)] += 1
        for d in (second_dr.get("key_drivers") or []):
            second_drivers[str(d)] += 1
        for o in (second_dr.get("objections") or []):
            second_objections[str(o)] += 1

        if first_label in _PURCHASE_DECISIONS:
            first_buyers += 1
            if lg.get("reordered"):
                reorderers += 1

        per_tick = lg.get("trust_by_tick") or {}
        for tick_key, val in per_tick.items():
            try:
                trust_by_tick.setdefault(int(tick_key), []).append(float(val))
            except (TypeError, ValueError):
                pass

    n = len(valid) or 1

    def _dist(counter: Counter) -> dict:
        return {
            k: {"count": v, "pct": round(100.0 * v / n, 1)}
            for k, v in counter.most_common()
        }

    avg_trust_by_tick = {
        tick: round(sum(vals) / len(vals), 4)
        for tick, vals in sorted(trust_by_tick.items())
        if vals
    }

    return {
        "journey_id": journey_id,
        "total_personas": len(logs),
        "errors": errors,
        "first_decision_distribution": _dist(first_decisions),
        "first_decision_drivers": dict(first_drivers.most_common(10)),
        "first_decision_objections": dict(first_objections.most_common(10)),
        "second_decision_distribution": _dist(second_decisions),
        "second_decision_drivers": dict(second_drivers.most_common(10)),
        "second_decision_objections": dict(second_objections.most_common(10)),
        "reorder_rate_pct": round(100.0 * reorderers / first_buyers, 2) if first_buyers else 0.0,
        "avg_trust_at_first_decision": 0.0,
        "avg_trust_at_second_decision": 0.0,
        "trust_by_tick": avg_trust_by_tick,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_simulatte_batch(
    personas: "list[PersonaRecord]",
    journey_config: "JourneyConfig",
    tier: str = "signal",
) -> dict:
    """Run a LittleJoys journey for all personas via the Simulatte cognitive loop.

    Drop-in replacement for LJ's run_batch. Returns a dict matching the schema
    produced by BatchResult.to_dict() so the LittleJoys Streamlit app reads
    it without modification.

    Args:
        personas: List of PersonaRecord objects.
        journey_config: JourneyConfig describing stimuli and decision ticks.
        tier: Simulation tier — "deep", "signal" (default), or "volume".

    Returns:
        dict with keys:
          journey_id        str
          total_personas    int
          errors            int
          elapsed_seconds   float
          aggregate         dict  (JourneyAggregate.to_dict() schema)
          logs              list[dict]  (one entry per persona)
    """
    resolved_tier = TIER_MAP.get(tier, SimulationTier.SIGNAL)
    total = len(personas)
    logs: list[dict] = []
    start = time.monotonic()

    async def _run_all() -> list[dict]:
        tasks = [
            _run_one_persona(persona, journey_config, resolved_tier)
            for persona in personas
        ]
        results: list[dict] = []
        for i, coro in enumerate(tasks):
            try:
                log = await coro
                logger.info(
                    "run_simulatte_batch: completed persona %d/%d (%s)",
                    i + 1,
                    total,
                    log.get("persona_id", "?"),
                )
            except Exception as exc:  # noqa: BLE001
                persona = personas[i]
                logger.exception(
                    "run_simulatte_batch: persona %s raised %s — recording error log",
                    getattr(persona, "persona_id", "?"),
                    exc,
                )
                log = _build_error_log(persona, journey_config, exc)
            results.append(log)
        return results

    logs = asyncio.run(_run_all())

    elapsed = round(time.monotonic() - start, 2)
    aggregate = _build_aggregate(logs, journey_config.journey_id)
    errors = sum(1 for lg in logs if lg.get("error"))

    return {
        "journey_id": journey_config.journey_id,
        "total_personas": total,
        "errors": errors,
        "elapsed_seconds": elapsed,
        "aggregate": aggregate,
        "logs": logs,
    }
