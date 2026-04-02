"""Tests for src/utils/llm_router.py and src/sarvam/llm_client.py provider properties."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.utils.llm_router import get_llm_client
from src.sarvam.llm_client import AnthropicLLMClient, SarvamLLMClient


@pytest.fixture()
def mock_anthropic():
    """A lightweight stand-in for an AsyncAnthropic client instance."""
    return MagicMock()


# ── Router tests ────────────────────────────────────────────────────────────────

def test_router_returns_anthropic_by_default(mock_anthropic):
    """get_llm_client() with no extra kwargs returns AnthropicLLMClient."""
    client = get_llm_client(mock_anthropic)
    assert isinstance(client, AnthropicLLMClient)
    assert client.provider == "anthropic"


def test_router_returns_sarvam_when_enabled_and_india(mock_anthropic):
    """sarvam_enabled=True + country='India' should yield a SarvamLLMClient."""
    with patch("os.environ.get", side_effect=lambda k, d="": "fake-key" if k == "SARVAM_API_KEY" else d):
        client = get_llm_client(mock_anthropic, sarvam_enabled=True, country="India")
    assert isinstance(client, SarvamLLMClient)
    assert client.provider == "sarvam"


def test_router_returns_anthropic_when_sarvam_enabled_but_not_india(mock_anthropic):
    """sarvam_enabled=True but country='UK' must still return AnthropicLLMClient."""
    client = get_llm_client(mock_anthropic, sarvam_enabled=True, country="UK")
    assert isinstance(client, AnthropicLLMClient)
    assert client.provider == "anthropic"


def test_router_returns_anthropic_when_sarvam_disabled_but_india(mock_anthropic):
    """sarvam_enabled=False + country='India' must return AnthropicLLMClient."""
    client = get_llm_client(mock_anthropic, sarvam_enabled=False, country="India")
    assert isinstance(client, AnthropicLLMClient)
    assert client.provider == "anthropic"


# ── SarvamLLMClient provider property tests ─────────────────────────────────────

def test_sarvam_client_provider_returns_anthropic_fallback_when_no_key(mock_anthropic):
    """SarvamLLMClient.provider == 'anthropic_fallback' when SARVAM_API_KEY is absent."""
    with patch("os.environ.get", side_effect=lambda k, d="": "" if k == "SARVAM_API_KEY" else d):
        client = SarvamLLMClient(fallback_anthropic_client=mock_anthropic)
    assert client.provider == "anthropic_fallback"
    assert not client.has_api_key


def test_anthropic_client_provider_returns_anthropic(mock_anthropic):
    """AnthropicLLMClient.provider always returns 'anthropic'."""
    client = AnthropicLLMClient(mock_anthropic)
    assert client.provider == "anthropic"
