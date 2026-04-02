"""tests/test_identity_constructor_routing.py — LLM router wiring into build().

Verifies that IdentityConstructor.build() automatically selects the correct
LLM client via get_llm_client() and passes it to LifeStoryGenerator.generate()
and NarrativeGenerator.generate().

Tests:
    1. test_build_uses_anthropic_client_by_default
       — sarvam_enabled=False → AnthropicLLMClient is selected and passed down.

    2. test_build_uses_sarvam_client_for_india_sarvam
       — sarvam_enabled=True + country=India → SarvamLLMClient is selected and
         passed to both generators (no real API calls).

    3. test_routing_decision_happens_after_anchor_set
       — The routed client type is determined by demographic_anchor.location.country,
         not a hard-coded default. UK → Anthropic; India+sarvam_enabled → Sarvam.

No live API calls. All LLM-calling components are mocked.
"""
from __future__ import annotations

import contextlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.generation.identity_constructor import IdentityConstructor, ICPSpec
from src.sarvam.llm_client import AnthropicLLMClient, SarvamLLMClient


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_demographic_anchor(country: str = "UK") -> MagicMock:
    """Return a minimal DemographicAnchor-like mock."""
    anchor = MagicMock()
    anchor.name = "Test Persona"
    anchor.age = 30
    anchor.gender = "female"
    anchor.location.country = country
    anchor.location.city = "London"
    anchor.location.region = "England"
    anchor.location.urban_tier = "metro"
    anchor.household.structure = "nuclear"
    anchor.household.size = 2
    anchor.household.income_bracket = "middle"
    anchor.household.dual_income = False
    anchor.life_stage = "young professional"
    anchor.education = "graduate"
    anchor.employment = "full-time"
    return anchor


def _make_icp_spec(sarvam_enabled: bool = False) -> ICPSpec:
    return ICPSpec(
        domain="cpg",
        mode="quick",
        sarvam_enabled=sarvam_enabled,
    )


def _make_mock_attributes() -> dict:
    return {"values": {}, "behaviour": {}, "digital": {}, "social": {}}


def _make_mock_derived_insights() -> MagicMock:
    di = MagicMock()
    di.decision_style = "deliberate"
    di.decision_style_score = 0.7
    di.primary_value_orientation = "quality"
    di.risk_appetite = "moderate"
    di.trust_anchor = "expert"
    di.key_tensions = ["price vs quality"]
    return di


def _make_mock_life_stories() -> list:
    story = MagicMock()
    story.title = "Career shift"
    story.when = "age 25"
    story.event = "Changed careers at 25."
    story.lasting_impact = "More risk averse."
    return [story]


def _make_mock_behavioural_tendencies() -> MagicMock:
    bt = MagicMock()
    bt.reasoning_prompt = "Tends to research before buying."
    bt.objection_profile = []
    bt.trust_orientation.dominant = "expert"
    bt.trust_orientation.weights.expert = 0.8
    bt.trust_orientation.weights.peer = 0.5
    bt.trust_orientation.weights.brand = 0.3
    bt.trust_orientation.weights.ad = 0.1
    bt.trust_orientation.weights.community = 0.2
    bt.trust_orientation.weights.influencer = 0.1
    return bt


def _make_mock_narrative() -> MagicMock:
    n = MagicMock()
    n.first_person = "I am a careful buyer who values quality above all else."
    n.third_person = "She is a methodical consumer who researches purchases thoroughly."
    n.display_name = "Test"
    return n


@contextlib.contextmanager
def _bypass_build_infrastructure(
    constructor,
    story_side_effect,
    narrative_side_effect,
    extra_patches=None,
):
    """Context manager that stubs all of build()'s sub-components except routing.

    Patches:
    - AttributeFiller.fill → mock attributes
    - DerivedInsightsComputer.compute → mock derived_insights
    - TendencyEstimator.estimate → mock behavioural_tendencies
    - story_generator.generate → caller-supplied side_effect
    - narrative_generator.generate → caller-supplied side_effect
    - PersonaRecord → MagicMock (bypasses Pydantic validation)
    - Memory → MagicMock (bypasses CoreMemory Pydantic requirement)
    - assemble_core_memory → MagicMock
    - PersonaValidator.validate_all → [MagicMock(passed=True)]

    extra_patches: optional list of additional patch() context managers.
    """
    mock_persona = MagicMock()
    mock_persona.mode = "quick"
    mock_persona.model_copy.return_value = mock_persona
    mock_persona.memory.core = MagicMock()
    mock_persona.memory.working = MagicMock()
    mock_persona.demographic_anchor.name = "Test Persona"

    stack = contextlib.ExitStack()
    if extra_patches:
        for p in extra_patches:
            stack.enter_context(p)

    stack.enter_context(patch(
        "src.generation.identity_constructor.AttributeFiller.fill",
        new=AsyncMock(return_value=_make_mock_attributes()),
    ))
    stack.enter_context(patch(
        "src.generation.identity_constructor.DerivedInsightsComputer.compute",
        return_value=_make_mock_derived_insights(),
    ))
    stack.enter_context(patch(
        "src.generation.identity_constructor.TendencyEstimator.estimate",
        return_value=_make_mock_behavioural_tendencies(),
    ))
    stack.enter_context(patch(
        "src.generation.identity_constructor.PersonaRecord",
        return_value=mock_persona,
    ))
    stack.enter_context(patch(
        "src.generation.identity_constructor.Memory",
        return_value=MagicMock(),
    ))
    stack.enter_context(patch(
        "src.generation.identity_constructor.assemble_core_memory",
        return_value=MagicMock(),
    ))
    stack.enter_context(patch(
        "src.generation.identity_constructor.PersonaValidator.validate_all",
        return_value=[MagicMock(passed=True)],
    ))
    stack.enter_context(patch.object(
        constructor.story_generator,
        "generate",
        side_effect=story_side_effect,
    ))
    stack.enter_context(patch.object(
        constructor.narrative_generator,
        "generate",
        side_effect=narrative_side_effect,
    ))

    with stack:
        yield


# ---------------------------------------------------------------------------
# Test 1 — Anthropic client by default (sarvam_enabled=False)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_uses_anthropic_client_by_default():
    """When sarvam_enabled=False, build() passes AnthropicLLMClient to both
    LifeStoryGenerator.generate() and NarrativeGenerator.generate()."""
    mock_anthropic_raw = MagicMock()
    constructor = IdentityConstructor(mock_anthropic_raw)

    anchor = _make_demographic_anchor(country="UK")
    icp = _make_icp_spec(sarvam_enabled=False)

    mock_stories = _make_mock_life_stories()
    mock_narrative_obj = _make_mock_narrative()

    captured_story_client: dict = {}
    captured_narrative_client: dict = {}

    async def fake_story_generate(*args, **kwargs):
        captured_story_client["client"] = kwargs.get("llm_client")
        return mock_stories

    async def fake_narrative_generate(*args, **kwargs):
        captured_narrative_client["client"] = kwargs.get("llm_client")
        return mock_narrative_obj

    with _bypass_build_infrastructure(constructor, fake_story_generate, fake_narrative_generate):
        await constructor.build(demographic_anchor=anchor, icp_spec=icp)

    assert "client" in captured_story_client, (
        "llm_client kwarg was not passed to story_generator.generate()"
    )
    assert isinstance(captured_story_client["client"], AnthropicLLMClient), (
        f"Expected AnthropicLLMClient, got {type(captured_story_client['client'])}"
    )

    assert "client" in captured_narrative_client, (
        "llm_client kwarg was not passed to narrative_generator.generate()"
    )
    assert isinstance(captured_narrative_client["client"], AnthropicLLMClient), (
        f"Expected AnthropicLLMClient, got {type(captured_narrative_client['client'])}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Sarvam client for India + sarvam_enabled=True
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_uses_sarvam_client_for_india_sarvam():
    """When sarvam_enabled=True and country=India, build() passes SarvamLLMClient
    to LifeStoryGenerator.generate() and NarrativeGenerator.generate()."""
    mock_anthropic_raw = MagicMock()
    constructor = IdentityConstructor(mock_anthropic_raw)

    anchor = _make_demographic_anchor(country="India")
    icp = _make_icp_spec(sarvam_enabled=True)

    mock_stories = _make_mock_life_stories()
    mock_narrative_obj = _make_mock_narrative()

    captured_story_client: dict = {}
    captured_narrative_client: dict = {}

    async def fake_story_generate(*args, **kwargs):
        captured_story_client["client"] = kwargs.get("llm_client")
        return mock_stories

    async def fake_narrative_generate(*args, **kwargs):
        captured_narrative_client["client"] = kwargs.get("llm_client")
        return mock_narrative_obj

    # Patch SARVAM_API_KEY so SarvamLLMClient sees a fake key
    sarvam_key_patch = patch(
        "os.environ.get",
        side_effect=lambda k, d="": "fake-key" if k == "SARVAM_API_KEY" else d,
    )

    with _bypass_build_infrastructure(
        constructor,
        fake_story_generate,
        fake_narrative_generate,
        extra_patches=[sarvam_key_patch],
    ):
        await constructor.build(demographic_anchor=anchor, icp_spec=icp)

    assert "client" in captured_story_client, (
        "llm_client kwarg was not passed to story_generator.generate()"
    )
    assert isinstance(captured_story_client["client"], SarvamLLMClient), (
        f"Expected SarvamLLMClient for India+sarvam_enabled, got {type(captured_story_client['client'])}"
    )

    assert "client" in captured_narrative_client, (
        "llm_client kwarg was not passed to narrative_generator.generate()"
    )
    assert isinstance(captured_narrative_client["client"], SarvamLLMClient), (
        f"Expected SarvamLLMClient for India+sarvam_enabled, got {type(captured_narrative_client['client'])}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Routing decision is driven by anchor country
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_routing_decision_happens_after_anchor_set():
    """Routing is determined by demographic_anchor.location.country.

    Case A: country='UK' with sarvam_enabled=True → AnthropicLLMClient
            (Sarvam only activates for India).
    Case B: country='India' with sarvam_enabled=True → SarvamLLMClient.

    This confirms the router reads the actual anchor country and is not
    defaulting to a hard-coded value.
    """
    mock_anthropic_raw = MagicMock()
    mock_stories = _make_mock_life_stories()
    mock_narrative_obj = _make_mock_narrative()

    # --- Case A: UK anchor + sarvam_enabled=True → AnthropicLLMClient ---
    constructor_a = IdentityConstructor(mock_anthropic_raw)
    anchor_uk = _make_demographic_anchor(country="UK")
    icp_a = _make_icp_spec(sarvam_enabled=True)  # enabled but not India

    captured_a: dict = {}

    async def story_a(*args, **kwargs):
        captured_a["client"] = kwargs.get("llm_client")
        return mock_stories

    with _bypass_build_infrastructure(
        constructor_a,
        story_a,
        AsyncMock(return_value=mock_narrative_obj),
    ):
        await constructor_a.build(demographic_anchor=anchor_uk, icp_spec=icp_a)

    assert isinstance(captured_a["client"], AnthropicLLMClient), (
        f"UK persona should use AnthropicLLMClient even when sarvam_enabled=True, "
        f"got {type(captured_a['client'])}"
    )

    # --- Case B: India anchor + sarvam_enabled=True → SarvamLLMClient ---
    constructor_b = IdentityConstructor(mock_anthropic_raw)
    anchor_india = _make_demographic_anchor(country="India")
    icp_b = _make_icp_spec(sarvam_enabled=True)

    captured_b: dict = {}

    async def story_b(*args, **kwargs):
        captured_b["client"] = kwargs.get("llm_client")
        return mock_stories

    sarvam_key_patch = patch(
        "os.environ.get",
        side_effect=lambda k, d="": "fake-key" if k == "SARVAM_API_KEY" else d,
    )

    with _bypass_build_infrastructure(
        constructor_b,
        story_b,
        AsyncMock(return_value=mock_narrative_obj),
        extra_patches=[sarvam_key_patch],
    ):
        await constructor_b.build(demographic_anchor=anchor_india, icp_spec=icp_b)

    assert isinstance(captured_b["client"], SarvamLLMClient), (
        f"India persona with sarvam_enabled=True should use SarvamLLMClient, "
        f"got {type(captured_b['client'])}"
    )
