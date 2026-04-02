"""LLM router — selects Anthropic or Sarvam client based on persona context.

Routing rule (per spec §15 Sprint 16):
    sarvam_enabled=True AND country="India"  →  SarvamLLMClient
    otherwise                                →  AnthropicLLMClient

The router is called once at the start of identity_constructor.build()
and the resulting client is passed down to all LLM callers.
"""
from __future__ import annotations
from typing import Any


def get_llm_client(
    anthropic_client: Any,
    *,
    sarvam_enabled: bool = False,
    country: str | None = None,
) -> "BaseLLMClient":  # noqa: F821
    """Return the appropriate LLM client for this persona's context.

    Args:
        anthropic_client: The AsyncAnthropic client instance (always required as fallback).
        sarvam_enabled: Whether Sarvam enrichment/generation is requested.
        country: The persona's country (from demographic_anchor.location.country).

    Returns:
        SarvamLLMClient if sarvam_enabled and country=="India", else AnthropicLLMClient.
    """
    from src.sarvam.llm_client import AnthropicLLMClient, SarvamLLMClient

    if sarvam_enabled and country == "India":
        return SarvamLLMClient(fallback_anthropic_client=anthropic_client)
    return AnthropicLLMClient(anthropic_client)
