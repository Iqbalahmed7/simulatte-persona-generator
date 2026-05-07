"""Tests for the LLM-driven DemographicAnchor sampler (PR-PG-3)."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.generation.anchor_sampler import sample_anchor_llm
from src.schema.persona import DemographicAnchor


def _mock_llm_client(payload: dict | str):
    """Build a fake AsyncAnthropic-shaped client whose messages.create returns
    a response object with .content[0].text equal to the JSON-encoded payload.
    """
    body = payload if isinstance(payload, str) else json.dumps(payload)
    response = SimpleNamespace(
        content=[SimpleNamespace(text=body)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=20),
    )
    create = AsyncMock(return_value=response)
    return SimpleNamespace(messages=SimpleNamespace(create=create)), create


_VALID_PAYLOAD = {
    "name": "Priya Sharma",
    "age": 34,
    "gender": "female",
    "location": {
        "country": "India",
        "region": "Maharashtra",
        "city": "Pune",
        "urban_tier": "metro",
    },
    "household": {
        "structure": "nuclear",
        "size": 4,
        "income_bracket": "middle",
        "dual_income": True,
    },
    "life_stage": "parent of school-age children",
    "education": "postgraduate",
    "employment": "full-time",
}


@pytest.mark.asyncio
async def test_sample_anchor_llm_returns_validated_anchor() -> None:
    client, create = _mock_llm_client(_VALID_PAYLOAD)
    anchor = await sample_anchor_llm(
        llm_client=client,
        business_problem="Why do urban Indian parents switch nutrition brands?",
        icp_description="Urban Indian working mothers, 30-45, with kids under 10",
        market="India",
        age_min=25,
        age_max=50,
        persona_index=2,
        domain="india_general",
    )
    assert isinstance(anchor, DemographicAnchor)
    assert anchor.name == "Priya Sharma"
    assert anchor.age == 34
    assert anchor.location.country == "India"
    assert anchor.worldview is None  # LLM path leaves worldview unset
    create.assert_awaited_once()


@pytest.mark.asyncio
async def test_sample_anchor_llm_strips_markdown_fence() -> None:
    fenced = "```json\n" + json.dumps(_VALID_PAYLOAD) + "\n```"
    client, _ = _mock_llm_client(fenced)
    anchor = await sample_anchor_llm(
        llm_client=client,
        business_problem="bp",
        icp_description="icp",
        market="India",
        age_min=25,
        age_max=50,
        persona_index=0,
    )
    assert anchor.name == "Priya Sharma"


@pytest.mark.asyncio
async def test_sample_anchor_llm_clamps_out_of_range_age() -> None:
    payload = dict(_VALID_PAYLOAD)
    payload["age"] = 99  # above age_max
    client, _ = _mock_llm_client(payload)
    anchor = await sample_anchor_llm(
        llm_client=client,
        business_problem="bp",
        icp_description="icp",
        market="India",
        age_min=25,
        age_max=50,
        persona_index=1,
    )
    assert 25 <= anchor.age <= 50


@pytest.mark.asyncio
async def test_sample_anchor_llm_propagates_validation_error() -> None:
    """Bad enum values should raise so callers can fall back to fixed pool."""
    payload = dict(_VALID_PAYLOAD)
    payload["education"] = "phd-candidate"  # not a valid Literal
    client, _ = _mock_llm_client(payload)
    with pytest.raises(Exception):
        await sample_anchor_llm(
            llm_client=client,
            business_problem="bp",
            icp_description="icp",
            market="India",
            age_min=25,
            age_max=50,
            persona_index=0,
        )
