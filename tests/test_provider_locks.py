"""Tests for quality-aware multi-provider routing.

Covers provider_locks.PROVIDER_LOCKS resolution and llm_router.get_client_for_stage
behaviour. Intentionally does NOT touch the legacy get_llm_client API — that
has its own tests in test_llm_router.py.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.sarvam.llm_client import AnthropicLLMClient
from src.utils.llm_router import get_client_for_stage, pick_run_provider
from src.utils.provider_locks import PROVIDER_LOCKS, get_stage_rule


@pytest.fixture()
def mock_anthropic():
    return MagicMock()


# ── Stage rule lookup ──────────────────────────────────────────────────────

def test_high_sensitivity_stages_are_anthropic_locked():
    """decide / synthesis / respond must be anthropic-pinned. This is the
    quality-preservation contract."""
    for stage in ("decide", "synthesis", "respond"):
        rule = get_stage_rule(stage)
        assert rule["sensitivity"] == "high"
        assert rule["locked_provider"] == "anthropic"


def test_unknown_stage_defaults_to_anthropic_lock():
    """Fail closed: unknown stages must NOT silently flex to OpenAI."""
    rule = get_stage_rule("not_a_real_stage_xyz")
    assert rule["locked_provider"] == "anthropic"


# ── Router resolution ─────────────────────────────────────────────────────

def test_locked_stage_always_returns_anthropic(mock_anthropic):
    """High-sensitivity stages return Anthropic even when run is OpenAI-pinned."""
    client = get_client_for_stage(
        "decide",
        anthropic_client=mock_anthropic,
        run_provider="openai",
    )
    assert isinstance(client, AnthropicLLMClient)


def test_capability_lock_overrides_run_provider(mock_anthropic):
    """web_search forces anthropic regardless of stage rule or run provider."""
    client = get_client_for_stage(
        "signal_tag",                       # normally flexible
        anthropic_client=mock_anthropic,
        run_provider="openai",
        capabilities=["web_search"],
    )
    assert isinstance(client, AnthropicLLMClient)


def test_flexible_stage_with_uncalibrated_run_provider_falls_back(mock_anthropic):
    """If run is pinned to a provider this stage hasn't been calibrated for,
    fall back to anthropic — never silently use the uncalibrated provider."""
    # frame_score is calibrated_for=["anthropic"] only
    client = get_client_for_stage(
        "frame_score",
        anthropic_client=mock_anthropic,
        run_provider="openai",  # not in calibrated_for
    )
    assert isinstance(client, AnthropicLLMClient)


def test_flexible_stage_honours_run_provider_when_calibrated(mock_anthropic):
    """If run is pinned to a calibrated provider, use it."""
    # signal_tag is calibrated_for=["anthropic", "openai"]
    with patch("src.utils.llm_router._is_configured", return_value=True), \
         patch("src.utils.openai_client.OpenAILLMClient.__init__", return_value=None):
        client = get_client_for_stage(
            "signal_tag",
            anthropic_client=mock_anthropic,
            run_provider="openai",
        )
    assert client.provider == "openai"


# ── pick_run_provider ──────────────────────────────────────────────────────

def test_pick_run_provider_defaults_to_anthropic():
    with patch("src.utils.llm_router._is_configured", return_value=True):
        assert pick_run_provider() == "anthropic"


def test_pick_run_provider_falls_back_when_openai_unconfigured():
    """Requesting openai without OPENAI_API_KEY → fall back to anthropic, don't crash."""
    def cfg(p):
        return p == "anthropic"  # only anthropic configured
    with patch("src.utils.llm_router._is_configured", side_effect=cfg):
        assert pick_run_provider(primary="openai") == "anthropic"


def test_pick_run_provider_capabilities_force_anthropic():
    """web_search forces anthropic at the run level too."""
    with patch("src.utils.llm_router._is_configured", return_value=True):
        assert pick_run_provider(
            primary="openai",
            capabilities_needed=["web_search"],
        ) == "anthropic"


# ── Lock taxonomy invariants ──────────────────────────────────────────────

def test_no_high_sensitivity_stage_is_flexible():
    """Belt-and-braces: no high-sensitivity stage may have locked_provider=None."""
    for stage, rule in PROVIDER_LOCKS.items():
        if rule.get("sensitivity") == "high":
            assert rule.get("locked_provider") is not None, (
                f"Stage '{stage}' is high-sensitivity but has no locked_provider — "
                f"this would allow silent quality degradation."
            )
