from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.generation.identity_constructor import ICPSpec, IdentityConstructor


def _make_anchor(country: str = "UK") -> SimpleNamespace:
    return SimpleNamespace(
        name="Test Persona",
        age=30,
        location=SimpleNamespace(country=country),
    )


def _make_icp(mode: str = "quick") -> ICPSpec:
    return ICPSpec(domain="cpg", mode=mode)


def _mock_components():
    attributes = {"values": {}, "behaviour": {}, "digital": {}, "social": {}}
    derived = MagicMock()
    derived.decision_style = "deliberate"
    derived.decision_style_score = 0.7
    derived.primary_value_orientation = "quality"
    derived.risk_appetite = "moderate"
    derived.trust_anchor = "expert"
    derived.key_tensions = ["price vs quality"]

    tendencies = MagicMock()
    tendencies.objection_profile = []
    tendencies.reasoning_prompt = "test"
    tendencies.trust_orientation = MagicMock()
    tendencies.trust_orientation.dominant = "expert"
    tendencies.trust_orientation.weights = MagicMock(
        expert=0.7, peer=0.5, brand=0.2, ad=0.1, community=0.3, influencer=0.2
    )

    life_story = MagicMock()
    life_story.title = "story"
    life_story.when = "age 20"
    life_story.event = "event"
    life_story.lasting_impact = "impact"

    narrative = MagicMock()
    narrative.first_person = "I choose carefully."
    narrative.third_person = "She chooses carefully."
    narrative.display_name = "Test"

    return attributes, derived, tendencies, [life_story], narrative


def _build_persona_stub():
    persona = MagicMock()
    persona.demographic_anchor = SimpleNamespace(name="Test Persona")
    persona.memory = SimpleNamespace(core=SimpleNamespace(), working=SimpleNamespace(observations=[]))

    def _model_copy(*, update):
        if "memory" in update:
            persona.memory = update["memory"]
        return persona

    persona.model_copy.side_effect = _model_copy
    return persona


@pytest.mark.asyncio
async def test_quick_mode_enables_narrative_validation_not_memory():
    constructor = IdentityConstructor(MagicMock())
    anchor = _make_anchor("UK")
    icp = _make_icp("quick")
    attrs, derived, tendencies, stories, narrative = _mock_components()
    persona = _build_persona_stub()

    with patch("src.generation.identity_constructor.AttributeFiller.fill", new=AsyncMock(return_value=attrs)), \
         patch("src.generation.identity_constructor.DerivedInsightsComputer.compute", return_value=derived), \
         patch("src.generation.identity_constructor.TendencyEstimator.estimate", return_value=tendencies), \
         patch.object(constructor.story_generator, "generate", new=AsyncMock(return_value=stories)), \
         patch.object(constructor.narrative_generator, "generate", new=AsyncMock(return_value=narrative)), \
         patch.object(constructor, "_assemble_core_memory", return_value=SimpleNamespace()), \
         patch("src.generation.identity_constructor.PersonaRecord", return_value=persona), \
         patch("src.generation.identity_constructor.Memory", side_effect=lambda core, working: SimpleNamespace(core=core, working=working)), \
         patch("src.generation.identity_constructor.assemble_core_memory", return_value=SimpleNamespace()), \
         patch("src.generation.identity_constructor.PersonaValidator.validate_all", return_value=[MagicMock(passed=True)]) as validate_all:
        await constructor.build(anchor, icp)

    validate_all.assert_called_once()
    _, kwargs = validate_all.call_args
    assert kwargs["include_narrative"] is True
    assert kwargs["include_memory"] is False


@pytest.mark.asyncio
async def test_simulation_ready_bootstraps_before_g10_validation():
    constructor = IdentityConstructor(MagicMock())
    anchor = _make_anchor("UK")
    icp = _make_icp("simulation-ready")
    attrs, derived, tendencies, stories, narrative = _mock_components()
    persona = _build_persona_stub()
    seeded_working = SimpleNamespace(observations=[1, 2, 3])

    def _validate_side_effect(persona_arg, include_narrative=False, include_memory=False):
        assert include_narrative is True
        assert include_memory is True
        assert persona_arg.memory.working is seeded_working
        return [MagicMock(passed=True)]

    with patch("src.generation.identity_constructor.AttributeFiller.fill", new=AsyncMock(return_value=attrs)), \
         patch("src.generation.identity_constructor.DerivedInsightsComputer.compute", return_value=derived), \
         patch("src.generation.identity_constructor.TendencyEstimator.estimate", return_value=tendencies), \
         patch.object(constructor.story_generator, "generate", new=AsyncMock(return_value=stories)), \
         patch.object(constructor.narrative_generator, "generate", new=AsyncMock(return_value=narrative)), \
         patch.object(constructor, "_assemble_core_memory", return_value=SimpleNamespace()), \
         patch("src.generation.identity_constructor.PersonaRecord", return_value=persona), \
         patch("src.generation.identity_constructor.Memory", side_effect=lambda core, working: SimpleNamespace(core=core, working=working)), \
         patch("src.generation.identity_constructor.assemble_core_memory", return_value=SimpleNamespace()), \
         patch("src.memory.seed_memory.bootstrap_seed_memories", return_value=seeded_working), \
         patch("src.generation.identity_constructor.PersonaValidator.validate_all", side_effect=_validate_side_effect):
        await constructor.build(anchor, icp)
