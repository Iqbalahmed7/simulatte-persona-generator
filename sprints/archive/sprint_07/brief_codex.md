# SPRINT 7 BRIEF — CODEX
**Role:** Simulation Structural Tests
**Sprint:** 7 — Temporal Simulation Modality
**Spec check:** Validity Protocol BV1, BV3, BV6
**Previous rating:** 20/20

---

## Your Job This Sprint

One file: `tests/test_simulation_structural.py`. Non-LLM structural tests that verify simulation output shape, turn log completeness, and report generation — using mocked `run_loop()`.

---

## File: `tests/test_simulation_structural.py`

### Test 1: TurnLog Shape

```python
@pytest.mark.asyncio
async def test_simulation_produces_correct_turn_logs():
    """
    Mock run_loop to return a fixed LoopResult.
    Assert: one TurnLog per stimulus per persona, fields populated correctly.
    """
    from unittest.mock import AsyncMock, patch
    from src.modalities.simulation import run_simulation
    from src.experiment.session import ExperimentSession
    from src.experiment.modality import ExperimentModality
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    import uuid

    persona = make_synthetic_persona()
    stimuli = ["Stimulus A", "Stimulus B", "Stimulus C"]
    session = ExperimentSession(
        session_id="struct-test-001",
        modality=ExperimentModality.TEMPORAL_SIMULATION,
        persona=persona,
        stimuli=stimuli,
    )

    mock_loop_result = _make_mock_loop_result()

    with patch("src.modalities.simulation.run_loop", new_callable=AsyncMock) as mock_loop:
        mock_loop.return_value = (persona, mock_loop_result)
        result = await run_simulation(session)

    assert result.total_turns == 3
    assert len(result.personas[0].turn_logs) == 3
    for i, log in enumerate(result.personas[0].turn_logs):
        assert log.turn == i
        assert log.stimulus == stimuli[i]
        assert log.observation_content == mock_loop_result.observation.content
```

### Test 2: Memory Accumulation (No Reset Between Turns)

```python
@pytest.mark.asyncio
async def test_simulation_accumulates_memory_across_turns():
    """
    Verify that run_loop is called with updated persona state on each turn
    (i.e., the persona from turn N is passed to turn N+1, not the original).
    """
    from unittest.mock import AsyncMock, patch, call
    from src.modalities.simulation import run_simulation
    from src.experiment.session import ExperimentSession
    from src.experiment.modality import ExperimentModality
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    import uuid

    persona = make_synthetic_persona()
    stimuli = ["S1", "S2"]
    session = ExperimentSession(
        session_id="mem-accum-001",
        modality=ExperimentModality.TEMPORAL_SIMULATION,
        persona=persona,
        stimuli=stimuli,
    )

    call_args_list = []

    async def capture_run_loop(stimulus, persona_arg, stimulus_id=None, decision_scenario=None):
        call_args_list.append((stimulus, persona_arg))
        # Return a new persona with an extra observation each call (simulating accumulation)
        from src.memory.working_memory import WorkingMemoryManager
        from tests.fixtures.synthetic_observation import make_synthetic_observation
        mgr = WorkingMemoryManager()
        obs = make_synthetic_observation(content=f"Obs for {stimulus}", importance=5)
        new_working = mgr.write_observation(persona_arg.memory.working, obs)
        from src.schema.persona import Memory
        updated_persona = persona_arg.model_copy(
            update={"memory": Memory(core=persona_arg.memory.core, working=new_working)}
        )
        return (updated_persona, _make_mock_loop_result())

    with patch("src.modalities.simulation.run_loop", side_effect=capture_run_loop):
        result = await run_simulation(session)

    # Turn 2 should receive persona with 1 observation (from turn 1), not the original empty persona
    _, persona_at_turn_2 = call_args_list[1]
    assert len(persona_at_turn_2.memory.working.observations) >= 1, (
        "Memory should accumulate — persona at turn 2 should have observations from turn 1"
    )
```

### Test 3: Report Generation from Simulation

```python
def test_simulation_report_attitude_arc():
    """
    Verify attitude arc has one AttitudePoint per turn.
    Verify decision_summaries only includes turns with decisions.
    """
    from src.modalities.simulation import SimulationResult, TurnLog, PersonaSimulationResult
    from src.modalities.simulation_report import generate_simulation_report
    from datetime import datetime, timezone

    # 3 turns: turn 0 no decision, turn 1 has decision, turn 2 no decision
    turn_logs = [
        TurnLog(turn=0, stimulus="S0", persona_id="p1", observation_content="obs0",
                observation_importance=5, observation_valence=0.2,
                reflected=False, decided=False, decision=None, confidence=None),
        TurnLog(turn=1, stimulus="S1", persona_id="p1", observation_content="obs1",
                observation_importance=7, observation_valence=0.4,
                reflected=False, decided=True, decision="Yes I would", confidence=75,
                key_drivers=["price"], reasoning_trace="Because price"),
        TurnLog(turn=2, stimulus="S2", persona_id="p1", observation_content="obs2",
                observation_importance=4, observation_valence=-0.1,
                reflected=False, decided=False, decision=None, confidence=None),
    ]
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    persona = make_synthetic_persona()
    per_result = PersonaSimulationResult(
        persona_id="p1", persona_name="Priya", turn_logs=turn_logs, final_persona_state=persona
    )
    sim_result = SimulationResult(
        simulation_id="test", session_id="s1",
        personas=[per_result], total_turns=3, stimuli=["S0", "S1", "S2"],
    )

    report = generate_simulation_report(sim_result)

    assert len(report.attitude_arc) == 3
    assert len(report.decision_summaries) == 1  # only turn 1 had a decision
    assert report.decision_summaries[0].turn == 1
```

### Helper

```python
def _make_mock_loop_result():
    from src.cognition.loop import LoopResult
    from tests.fixtures.synthetic_observation import make_synthetic_observation
    obs = make_synthetic_observation(content="Mock observation content", importance=5, emotional_valence=0.1)
    return LoopResult(observation=obs, reflections=[], decision=None, reflected=False, decided=False)
```

---

## Constraints

- No LLM calls. Patch `src.modalities.simulation.run_loop`.
- Patch target is the import site, not the source module.
- All 3 tests should pass without `--integration`.

---

## Outcome File

When done, write `sprints/outcome_codex.md` with:
1. File created (line count)
2. Test results (pass/fail)
3. Memory accumulation test — how you verified persona state threading
4. Known gaps
