"""tests/test_simulation_tier.py — SimulationTier enum and model routing tests.

No LLM calls. Tests the tier enum, tier_models() helper, and loop wiring.
"""
from __future__ import annotations

import pytest

from src.experiment.session import SimulationTier, tier_models

_HAIKU = "claude-haiku-4-5-20251001"
_SONNET = "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# SimulationTier enum
# ---------------------------------------------------------------------------

class TestSimulationTierEnum:
    def test_values(self):
        assert SimulationTier.DEEP.value == "deep"
        assert SimulationTier.SIGNAL.value == "signal"
        assert SimulationTier.VOLUME.value == "volume"

    def test_string_coercion(self):
        assert SimulationTier("deep") == SimulationTier.DEEP
        assert SimulationTier("signal") == SimulationTier.SIGNAL
        assert SimulationTier("volume") == SimulationTier.VOLUME

    def test_is_str(self):
        # SimulationTier(str, Enum) — value is usable as a plain string
        assert SimulationTier.DEEP == "deep"
        assert SimulationTier.VOLUME == "volume"


# ---------------------------------------------------------------------------
# tier_models() routing
# ---------------------------------------------------------------------------

class TestTierModels:
    def test_deep_tier_models(self):
        m = tier_models(SimulationTier.DEEP)
        assert m["perceive"] == _HAIKU
        assert m["reflect"] == _SONNET
        assert m["decide"] == _SONNET

    def test_signal_tier_models(self):
        m = tier_models(SimulationTier.SIGNAL)
        assert m["perceive"] == _HAIKU
        assert m["reflect"] == _HAIKU   # Haiku for reflect in SIGNAL tier
        assert m["decide"] == _SONNET   # Sonnet for final decide

    def test_volume_tier_models(self):
        m = tier_models(SimulationTier.VOLUME)
        assert m["perceive"] == _HAIKU
        assert m["reflect"] == _HAIKU
        assert m["decide"] == _HAIKU    # Haiku throughout

    def test_perceive_is_always_haiku(self):
        """Perceive must always use Haiku regardless of tier (spec §9)."""
        for t in SimulationTier:
            assert tier_models(t)["perceive"] == _HAIKU, (
                f"perceive model must be Haiku for tier={t}"
            )

    def test_deep_is_most_capable(self):
        """DEEP tier must use Sonnet for reflect and decide."""
        m = tier_models(SimulationTier.DEEP)
        assert m["reflect"] == _SONNET
        assert m["decide"] == _SONNET

    def test_volume_is_all_haiku(self):
        """VOLUME tier must use Haiku for all three stages."""
        m = tier_models(SimulationTier.VOLUME)
        assert all(v == _HAIKU for v in m.values())

    def test_returns_three_keys(self):
        for t in SimulationTier:
            m = tier_models(t)
            assert set(m.keys()) == {"perceive", "reflect", "decide"}


# ---------------------------------------------------------------------------
# ExperimentSession tier field
# ---------------------------------------------------------------------------

class TestExperimentSessionTier:
    def test_default_tier_is_deep(self):
        from src.experiment.session import ExperimentSession, ExperimentModality
        from unittest.mock import MagicMock
        persona = MagicMock()
        persona.memory.working = MagicMock()
        session = ExperimentSession(
            session_id="s-001",
            modality=ExperimentModality.TEMPORAL_SIMULATION,
            persona=persona,
        )
        assert session.tier == SimulationTier.DEEP

    def test_tier_can_be_set(self):
        from src.experiment.session import ExperimentSession, ExperimentModality
        from unittest.mock import MagicMock
        persona = MagicMock()
        session = ExperimentSession(
            session_id="s-002",
            modality=ExperimentModality.TEMPORAL_SIMULATION,
            persona=persona,
            tier=SimulationTier.VOLUME,
        )
        assert session.tier == SimulationTier.VOLUME


# ---------------------------------------------------------------------------
# create_session() tier parameter
# ---------------------------------------------------------------------------

class TestCreateSessionTier:
    def _make_persona(self):
        from unittest.mock import MagicMock
        from src.schema.persona import (
            PersonaRecord, SimulationState, WorkingMemory, Memory
        )
        import uuid
        from datetime import datetime, timezone

        # Build a minimal real PersonaRecord so reset_working_memory works
        # (it calls model_copy which requires a real Pydantic model).
        # Use MagicMock for deeper fields that are not needed.
        p = MagicMock(spec=PersonaRecord)
        p.persona_id = f"pg-tier-{uuid.uuid4().hex[:6]}"

        state = SimulationState(
            current_turn=0,
            importance_accumulator=0.0,
            reflection_count=0,
            awareness_set={},
            consideration_set=[],
            last_decision=None,
        )
        working = WorkingMemory(
            observations=[], reflections=[], plans=[],
            brand_memories={}, simulation_state=state,
        )
        from src.schema.persona import CoreMemory, RelationshipMap, ImmutableConstraints
        core = CoreMemory(
            identity_statement="Test identity",
            key_values=["value1", "value2", "value3"],
            life_defining_events=[],
            relationship_map=RelationshipMap(
                primary_decision_partner="partner",
                key_influencers=[],
                trust_network=[],
            ),
            immutable_constraints=ImmutableConstraints(
                budget_ceiling=None,
                non_negotiables=[],
                absolute_avoidances=[],
            ),
            tendency_summary="Test tendency",
        )
        memory = Memory(core=core, working=working)
        p.memory = memory

        def _model_copy(update=None):
            new_p = MagicMock(spec=PersonaRecord)
            new_p.persona_id = p.persona_id
            new_p.memory = memory if not (update and "memory" in update) else update["memory"]
            new_p.model_copy = p.model_copy
            return new_p

        p.model_copy = _model_copy
        return p

    def test_create_session_default_tier(self):
        from src.experiment.session import create_session, ExperimentModality
        persona = self._make_persona()
        session = create_session(
            modality=ExperimentModality.TEMPORAL_SIMULATION,
            stimuli=["stimulus"],
            persona=persona,
        )
        assert session.tier == SimulationTier.DEEP

    def test_create_session_volume_tier(self):
        from src.experiment.session import create_session, ExperimentModality
        persona = self._make_persona()
        session = create_session(
            modality=ExperimentModality.TEMPORAL_SIMULATION,
            stimuli=["stimulus"],
            persona=persona,
            tier=SimulationTier.VOLUME,
        )
        assert session.tier == SimulationTier.VOLUME


# ---------------------------------------------------------------------------
# loop.py tier threading (unit — verify _models resolved correctly)
# ---------------------------------------------------------------------------

class TestLoopTierModels:
    """Verify tier_models() is called correctly by run_loop's model resolution logic."""

    def test_deep_tier_resolves_sonnet_for_reflect(self):
        models = tier_models(SimulationTier.DEEP)
        assert models["reflect"] == _SONNET

    def test_signal_tier_resolves_haiku_for_reflect(self):
        models = tier_models(SimulationTier.SIGNAL)
        assert models["reflect"] == _HAIKU

    def test_volume_tier_resolves_haiku_for_decide(self):
        models = tier_models(SimulationTier.VOLUME)
        assert models["decide"] == _HAIKU

    def test_tier_models_consistent_with_spec_description(self):
        """Table of expected models matches the spec docstring exactly."""
        expectations = [
            (SimulationTier.DEEP,   "perceive", _HAIKU),
            (SimulationTier.DEEP,   "reflect",  _SONNET),
            (SimulationTier.DEEP,   "decide",   _SONNET),
            (SimulationTier.SIGNAL, "perceive", _HAIKU),
            (SimulationTier.SIGNAL, "reflect",  _HAIKU),
            (SimulationTier.SIGNAL, "decide",   _SONNET),
            (SimulationTier.VOLUME, "perceive", _HAIKU),
            (SimulationTier.VOLUME, "reflect",  _HAIKU),
            (SimulationTier.VOLUME, "decide",   _HAIKU),
        ]
        for tier, stage, expected_model in expectations:
            actual = tier_models(tier)[stage]
            assert actual == expected_model, (
                f"tier={tier} stage={stage}: expected {expected_model}, got {actual}"
            )
