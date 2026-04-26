"""tests/test_structured_outputs.py — BRIEF-013 structured outputs migration tests.

4 tests:
1. test_perceive_uses_tool_use — mock returns tool_use block, verify perceive parses it
2. test_decide_uses_tool_use  — same for decide
3. test_reflect_uses_tool_use  — same for reflect
4. test_falls_back_to_text_parser_on_no_tool_use — text-only fallback path

No live API calls. All mock objects constructed inline.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Minimal mock persona factory
# ---------------------------------------------------------------------------

def _make_persona() -> object:
    """Return the minimal PersonaRecord-shaped object needed by cognition calls.

    Uses SimpleNamespace throughout so we don't need to satisfy Pydantic.
    """
    now = datetime.now(tz=timezone.utc)

    # ImmutableConstraints
    constraints = SimpleNamespace(
        budget_ceiling=None,
        non_negotiables=[],
        absolute_avoidances=[],
    )

    # CoreMemory
    core = SimpleNamespace(
        identity_statement="I am a test persona.",
        key_values=["honesty", "family", "community"],
        tendency_summary="I tend to be cautious and deliberate.",
        immutable_constraints=constraints,
        relationship_map=SimpleNamespace(primary_decision_partner="my spouse"),
        # Optional India-specific attrs
        current_conditions_stance=None,
        media_trust_stance=None,
        gender_norms_stance=None,
        governance_stance=None,
        inc_stance=None,
        cultural_context=None,
    )

    # WorkingMemory
    memory = SimpleNamespace(core=core)

    # DemographicAnchor — worldview needed by _get_political_lean()
    worldview = SimpleNamespace(
        political_profile=SimpleNamespace(archetype=None),
    )
    demographic_anchor = SimpleNamespace(
        name="Test Persona",
        worldview=worldview,
        attributes={},
    )

    # DerivedInsights
    derived_insights = SimpleNamespace(consistency_score=75)

    return SimpleNamespace(
        persona_id=str(uuid.uuid4()),
        memory=memory,
        demographic_anchor=demographic_anchor,
        derived_insights=derived_insights,
        # _get_political_lean() falls back to persona.attributes["worldview"]
        attributes={},
    )


def _make_tool_use_response(tool_name: str, tool_input: dict) -> object:
    """Return a minimal Anthropic response object containing a tool_use block."""
    tool_block = SimpleNamespace(type="tool_use", name=tool_name, input=tool_input)
    return SimpleNamespace(content=[tool_block])


def _make_text_response(text: str) -> object:
    """Return a minimal Anthropic response object containing only a text block."""
    text_block = SimpleNamespace(type="text", text=text)
    return SimpleNamespace(content=[text_block])


# ---------------------------------------------------------------------------
# Test 1: perceive uses tool_use block
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_perceive_uses_tool_use():
    """perceive() extracts the result from a tool_use block, not .text."""
    from src.cognition.perceive import perceive
    from src.schema.persona import Observation

    persona = _make_persona()
    perceive_input = {
        "content": "This product looks interesting to me.",
        "importance": 7,
        "emotional_valence": 0.5,
    }
    mock_response = _make_tool_use_response("emit_perception", perceive_input)

    with patch(
        "src.cognition.perceive.api_call_with_retry",
        new=AsyncMock(return_value=mock_response),
    ):
        result = await perceive("A new product ad", persona)

    assert isinstance(result, Observation)
    assert result.content == "This product looks interesting to me."
    assert result.importance == 7
    assert abs(result.emotional_valence - 0.5) < 0.001


# ---------------------------------------------------------------------------
# Test 2: decide uses tool_use block
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_decide_uses_tool_use():
    """decide() extracts the result from a tool_use block, not .text."""
    from src.cognition.decide import decide, DecisionOutput

    persona = _make_persona()
    decide_input = {
        "gut_reaction": "Looks good to me.",
        "information_processing": "I focus on value for money.",
        "constraint_check": "Within budget.",
        "social_signal_check": "My spouse would approve.",
        "final_decision": "buy",
        "confidence": 80,
        "key_drivers": ["price", "quality"],
        "objections": ["uncertain brand"],
        "what_would_change_mind": "A negative review.",
        "follow_up_action": "Orders online tonight.",
        "implied_purchase": False,
    }
    mock_response = _make_tool_use_response("emit_decision", decide_input)

    with patch(
        "src.cognition.decide.api_call_with_retry",
        new=AsyncMock(return_value=mock_response),
    ):
        result = await decide(
            scenario="Should I buy this product?",
            memories=[],
            persona=persona,
            apply_noise=False,
        )

    assert isinstance(result, DecisionOutput)
    assert result.decision == "buy"
    assert result.gut_reaction == "Looks good to me."
    assert result.confidence == 80
    assert result.key_drivers == ["price", "quality"]
    assert result.implied_purchase is False


# ---------------------------------------------------------------------------
# Test 3: reflect uses tool_use block
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reflect_uses_tool_use():
    """reflect() extracts items from a tool_use block wrapper, not .text."""
    from src.cognition.reflect import reflect
    from src.schema.persona import Observation, Reflection

    persona = _make_persona()

    # Build 5 minimal observations (reflect requires >= 5)
    obs_ids = [str(uuid.uuid4()) for _ in range(5)]
    now = datetime.now(tz=timezone.utc)
    observations = [
        Observation(
            id=obs_ids[i],
            timestamp=now,
            type="observation",
            content=f"Observation {i}",
            importance=5,
            emotional_valence=0.0,
            source_stimulus_id=None,
            last_accessed=now,
        )
        for i in range(5)
    ]

    reflect_input = {
        "items": [
            {
                "content": "I am becoming more price-conscious.",
                "importance": 6,
                "emotional_valence": -0.2,
                "source_observation_ids": [obs_ids[0], obs_ids[1]],
            },
            {
                "content": "Community feedback shapes my choices.",
                "importance": 5,
                "emotional_valence": 0.1,
                "source_observation_ids": [obs_ids[2], obs_ids[3]],
            },
        ]
    }
    mock_response = _make_tool_use_response("emit_reflections", reflect_input)

    with patch(
        "src.cognition.reflect.api_call_with_retry",
        new=AsyncMock(return_value=mock_response),
    ):
        result = await reflect(observations, persona)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(r, Reflection) for r in result)
    assert result[0].content == "I am becoming more price-conscious."
    assert result[1].content == "Community feedback shapes my choices."


# ---------------------------------------------------------------------------
# Test 4: fallback to text parser when no tool_use block returned
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_falls_back_to_text_parser_on_no_tool_use():
    """When the API returns text instead of tool_use, perceive falls back to
    the text JSON parser and still returns a valid Observation."""
    from src.cognition.perceive import perceive
    from src.schema.persona import Observation

    persona = _make_persona()

    # Response with only a text block (no tool_use)
    raw_json = '{"content": "Fallback response.", "importance": 4, "emotional_valence": -0.1}'
    mock_response = _make_text_response(raw_json)

    with patch(
        "src.cognition.perceive.api_call_with_retry",
        new=AsyncMock(return_value=mock_response),
    ):
        result = await perceive("Some stimulus", persona)

    assert isinstance(result, Observation)
    assert result.content == "Fallback response."
    assert result.importance == 4
    assert abs(result.emotional_valence - (-0.1)) < 0.001
