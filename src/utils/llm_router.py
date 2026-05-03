"""LLM router — quality-aware multi-provider routing.

Two APIs:

1. `get_llm_client(...)` — legacy. Routes Anthropic vs Sarvam by country.
   Kept for backward compat; existing callers don't need to change.

2. `get_client_for_stage(stage, run_provider=None, ...)` — new quality-aware
   path. Reads PROVIDER_LOCKS, returns the right client for that stage,
   pinning to the run-level provider once the run starts so cohorts don't
   drift mid-pipeline.

When adding a new LLM caller, prefer #2 and register the stage in
`provider_locks.py` first.
"""
from __future__ import annotations
import logging
import os
from typing import Any

from src.utils.provider_locks import (
    CAPABILITY_LOCKS,
    PROVIDER_LOCKS,
    Provider,
    get_stage_rule,
)

logger = logging.getLogger(__name__)


# ── Legacy API (Sarvam routing) — unchanged ────────────────────────────────

def get_llm_client(
    anthropic_client: Any,
    *,
    sarvam_enabled: bool = False,
    country: str | None = None,
) -> "BaseLLMClient":  # noqa: F821
    """Legacy router: Anthropic vs Sarvam by country.

    Used by identity_constructor.build(). Do not extend — for new callers,
    use `get_client_for_stage` which is quality-aware.
    """
    from src.sarvam.llm_client import AnthropicLLMClient, SarvamLLMClient

    if sarvam_enabled and country == "India":
        return SarvamLLMClient(fallback_anthropic_client=anthropic_client)
    return AnthropicLLMClient(anthropic_client)


# ── New quality-aware API ─────────────────────────────────────────────────

def get_client_for_stage(
    stage: str,
    *,
    anthropic_client: Any,
    run_provider: Provider | None = None,
    capabilities: list[str] | None = None,
) -> "BaseLLMClient":  # noqa: F821
    """Return the right LLM client for a pipeline stage.

    Args:
        stage: Stage name (must be in provider_locks.PROVIDER_LOCKS).
        anthropic_client: Pre-built AsyncAnthropic instance — always required
            because Anthropic is the default fallback.
        run_provider: If set, the run has already pinned to this provider;
            honour the pin unless the stage's lock overrides it. Pass the
            return value through the pipeline to keep the cohort coherent.
        capabilities: Required capabilities ("web_search", "image_gen") —
            forces a provider regardless of stage rule.

    Resolution order:
        1. Capability lock (e.g. web_search → anthropic always)
        2. Stage lock (high-sensitivity stages pinned)
        3. Run-pinned provider (if compatible with stage's calibrated_for)
        4. Stage's prefer_cheap → cheapest calibrated provider
        5. Default → anthropic

    Raises:
        ProviderNotConfigured: candidate provider has no API key.
    """
    from src.sarvam.llm_client import AnthropicLLMClient

    # 1. Capability lock — non-negotiable
    if capabilities:
        for cap in capabilities:
            if cap in CAPABILITY_LOCKS:
                forced = CAPABILITY_LOCKS[cap]
                logger.debug("[router] %s: capability=%s → %s", stage, cap, forced)
                return _build_client(forced, anthropic_client)

    rule = get_stage_rule(stage)

    # 2. Stage lock
    locked = rule.get("locked_provider")
    if locked is not None:
        logger.debug("[router] %s: stage-locked → %s", stage, locked)
        return _build_client(locked, anthropic_client)

    # 3. Run-pinned (if calibrated for this stage)
    calibrated = rule.get("calibrated_for", ["anthropic"])
    if run_provider and run_provider in calibrated:
        logger.debug("[router] %s: run-pinned → %s", stage, run_provider)
        return _build_client(run_provider, anthropic_client)
    if run_provider and run_provider not in calibrated:
        logger.info(
            "[router] %s: run pinned to %s but stage only calibrated for %s — "
            "using anthropic",
            stage, run_provider, calibrated,
        )
        return AnthropicLLMClient(anthropic_client)

    # 4. Prefer-cheap (within calibrated set)
    if rule.get("prefer_cheap"):
        for candidate in _CHEAP_ORDER:
            if candidate in calibrated and _is_configured(candidate):
                logger.debug("[router] %s: cheap-pref → %s", stage, candidate)
                return _build_client(candidate, anthropic_client)

    # 5. Default
    return AnthropicLLMClient(anthropic_client)


# Cheap-first ordering used when prefer_cheap=True
_CHEAP_ORDER: list[Provider] = ["openai", "anthropic"]


def pick_run_provider(
    *,
    primary: Provider = "anthropic",
    capabilities_needed: list[str] | None = None,
) -> Provider:
    """Pick the provider to pin for an entire run.

    Call this ONCE at run start. Pass the result to every
    get_client_for_stage(run_provider=...) call so the run is internally
    coherent.

    The default is anthropic — explicit override required to switch the
    whole run to a different primary.
    """
    if capabilities_needed:
        for cap in capabilities_needed:
            if cap in CAPABILITY_LOCKS:
                return CAPABILITY_LOCKS[cap]

    if primary == "anthropic" and not _is_configured("anthropic"):
        raise RuntimeError("ANTHROPIC_API_KEY not set — no primary provider available")
    if primary == "openai" and not _is_configured("openai"):
        logger.warning("[router] openai requested but not configured — falling back to anthropic")
        return "anthropic"

    return primary


# ── Internals ──────────────────────────────────────────────────────────────

def _is_configured(provider: Provider) -> bool:
    if provider == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    if provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY", "").strip())
    if provider == "sarvam":
        return bool(os.environ.get("SARVAM_API_KEY", "").strip())
    return False


def _build_client(provider: Provider, anthropic_client: Any) -> "BaseLLMClient":  # noqa: F821
    from src.sarvam.llm_client import AnthropicLLMClient, SarvamLLMClient

    if provider == "anthropic":
        return AnthropicLLMClient(anthropic_client)
    if provider == "openai":
        from src.utils.openai_client import OpenAILLMClient
        return OpenAILLMClient()
    if provider == "sarvam":
        return SarvamLLMClient(fallback_anthropic_client=anthropic_client)
    raise ValueError(f"Unknown provider: {provider}")
