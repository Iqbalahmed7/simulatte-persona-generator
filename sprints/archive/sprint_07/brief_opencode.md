# SPRINT 7 BRIEF — OPENCODE
**Role:** Simulation Report + S1/S2 Quality Gates
**Sprint:** 7 — Temporal Simulation Modality
**Spec check:** Master Spec §12 (Simulation Quality Gates S1–S4)
**Previous rating:** 19/20

---

## Your Job This Sprint

Two files: the simulation report formatter and the S1/S2 simulation quality gate checks.

---

## File 1: `src/modalities/simulation_report.py`

### Interface

```python
from src.modalities.simulation import SimulationResult, TurnLog, PersonaSimulationResult
from dataclasses import dataclass, field

@dataclass
class AttitudePoint:
    turn: int
    avg_confidence: float      # mean confidence across all personas at this turn (None turns excluded)
    avg_valence: float         # mean observation emotional_valence at this turn
    reflection_fired: bool     # True if any persona reflected at this turn

@dataclass
class DecisionSummary:
    turn: int
    stimulus: str
    decision_distribution: dict[str, int]   # normalized decision → count
    avg_confidence: float
    divergence_flag: bool                   # True if no decision > 50% of deciding personas

@dataclass
class SimulationReport:
    simulation_id: str
    cohort_size: int
    total_turns: int
    attitude_arc: list[AttitudePoint]          # one per turn
    decision_summaries: list[DecisionSummary]  # only turns where decisions were made
    per_persona_logs: dict[str, list[TurnLog]] # persona_id → turn logs

def generate_simulation_report(result: SimulationResult) -> SimulationReport:
    """
    Compute SimulationReport from SimulationResult.
    All computation is deterministic — no LLM calls.
    """
    ...
```

### Attitude Arc

For each turn index, collect all `TurnLog.observation_valence` values across personas. Average them. Collect `TurnLog.confidence` values for turns where `decided=True`. The `AttitudePoint.avg_confidence` is None (expressed as 0.0) when no persona made a decision that turn.

### Decision Summary

Only generate a `DecisionSummary` for turns where `decided=True` for at least one persona. Use the same decision normalization as `survey_report.py`:
```python
def _normalize_decision(text: str) -> str:
    t = text.lower().strip()
    if t.startswith("yes"): return "yes"
    if t.startswith("no"): return "no"
    return t[:40]
```

---

## File 2: `tests/test_simulation_e2e.py`

### S1: Zero Error Rate

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_s1_simulation_completes_without_error():
    """
    S1: 5-persona trial run completes without error.
    10 stimuli. No decision scenarios.
    """
    from src.modalities.simulation import run_simulation
    from src.experiment.session import create_session
    from src.experiment.modality import ExperimentModality
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    personas = [make_synthetic_persona() for _ in range(5)]
    # Build a simple cohort-like container
    stimuli = [
        "A new household cleaner brand launches with a focus on natural ingredients.",
        "A price comparison app shows your usual brand is 30% more expensive than alternatives.",
        "Your neighbour recommends a new grocery delivery service.",
        "A news article highlights health concerns about a common food additive.",
        "A loyalty program from your regular supermarket offers double points this week.",
        "A friend shares a positive review of a premium cooking oil brand.",
        "Your usual brand runs out of stock at the store.",
        "A new convenience store opens near your home.",
        "A social media post from a trusted influencer promotes a health supplement.",
        "The price of your favourite product increases by 15%.",
    ]

    from src.experiment.session import ExperimentSession
    from src.experiment.modality import ExperimentModality
    import uuid

    session = ExperimentSession(
        session_id=f"s1-test-{uuid.uuid4().hex[:6]}",
        modality=ExperimentModality.TEMPORAL_SIMULATION,
        persona=personas[0],
        stimuli=stimuli,
    )

    result = await run_simulation(session)

    assert result.total_turns == 10
    assert len(result.personas) == 1
    assert len(result.personas[0].turn_logs) == 10
```

### S2: Decision Diversity

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_s2_no_single_decision_dominates():
    """
    S2: No single decision > 90% of cohort on any decision turn.
    Run 3 personas through 3 stimuli with decision scenarios.
    """
    from src.modalities.simulation import run_simulation
    from src.modalities.simulation_report import generate_simulation_report
    from src.experiment.session import ExperimentSession
    from src.experiment.modality import ExperimentModality
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    import uuid

    personas = [make_synthetic_persona() for _ in range(3)]
    stimuli = [
        "A premium brand launches a new product at twice the usual price.",
        "A trusted friend recommends switching to a new brand.",
        "A significant discount is offered on a premium product.",
    ]
    decision_scenarios = [
        "Do you buy this premium product at twice the usual price?",
        "Do you switch to the new brand your friend recommended?",
        "Do you take advantage of this discount on the premium product?",
    ]

    session = ExperimentSession(
        session_id=f"s2-test-{uuid.uuid4().hex[:6]}",
        modality=ExperimentModality.TEMPORAL_SIMULATION,
        persona=personas[0],
        stimuli=stimuli,
        decision_scenarios=decision_scenarios,
    )

    result = await run_simulation(session)
    report = generate_simulation_report(result)

    for summary in report.decision_summaries:
        total = sum(summary.decision_distribution.values())
        if total > 0:
            max_share = max(summary.decision_distribution.values()) / total
            assert max_share <= 0.90, (
                f"S2 FAIL: {max_share:.0%} of personas made the same decision on turn {summary.turn}"
            )
```

---

## Integration Contract

- `from src.modalities.simulation import SimulationResult, TurnLog, PersonaSimulationResult`
- `from src.experiment.session import ExperimentSession, create_session`

---

## Outcome File

When done, write `sprints/outcome_opencode.md` with:
1. Files created (line counts)
2. Attitude arc computation — how confidence and valence are aggregated
3. S1 and S2 test design
4. Known gaps
