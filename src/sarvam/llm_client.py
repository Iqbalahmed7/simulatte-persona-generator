"""LLM client abstraction for Simulatte persona generation.

Provides a unified interface over Anthropic (Claude) and Sarvam APIs.
The caller always calls client.complete(system, messages, max_tokens, model)
and gets back a string response — regardless of which provider is in use.
"""
from __future__ import annotations
import os
from abc import ABC, abstractmethod
from typing import Any


class BaseLLMClient(ABC):
    """Unified interface for LLM completion calls."""

    @abstractmethod
    async def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int = 1024,
        model: str | None = None,
    ) -> str:
        """Return the text response from the LLM."""
        ...

    @property
    @abstractmethod
    def provider(self) -> str:
        """Return provider name: 'anthropic' or 'sarvam'."""
        ...


class AnthropicLLMClient(BaseLLMClient):
    """Wraps an AsyncAnthropic client to match BaseLLMClient interface."""

    def __init__(self, client: Any) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "anthropic"

    async def complete(self, *, system: str, messages: list[dict], max_tokens: int = 1024, model: str | None = None) -> str:
        from src.utils.retry import api_call_with_retry
        response = await api_call_with_retry(
            self._client.messages.create,
            model=model or "claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text


class SarvamLLMClient(BaseLLMClient):
    """Calls Sarvam AI's text generation API.

    Sarvam API is OpenAI-compatible:
        POST https://api.sarvam.ai/v1/chat/completions
        Authorization: Bearer {SARVAM_API_KEY}
        Body: { "model": "sarvam-m", "messages": [...], "max_tokens": N }

    Falls back to AnthropicLLMClient if SARVAM_API_KEY is not set.
    """

    SARVAM_BASE_URL = "https://api.sarvam.ai/v1"
    DEFAULT_MODEL = "sarvam-m"

    def __init__(self, fallback_anthropic_client: Any | None = None) -> None:
        self._api_key = os.environ.get("SARVAM_API_KEY", "")
        self._fallback = fallback_anthropic_client
        if not self._api_key and fallback_anthropic_client is None:
            raise ValueError(
                "SarvamLLMClient requires either SARVAM_API_KEY env var "
                "or a fallback_anthropic_client"
            )

    @property
    def provider(self) -> str:
        return "sarvam" if self._api_key else "anthropic_fallback"

    @property
    def has_api_key(self) -> bool:
        return bool(self._api_key)

    async def complete(self, *, system: str, messages: list[dict], max_tokens: int = 1024, model: str | None = None) -> str:
        if not self._api_key:
            # No Sarvam key — fall back to Anthropic with a warning
            import warnings
            warnings.warn(
                "SARVAM_API_KEY not set — falling back to Anthropic for Indian persona generation. "
                "Set SARVAM_API_KEY to enable authentic Sarvam-powered Indian personas.",
                stacklevel=2,
            )
            if self._fallback:
                from src.sarvam.llm_client import AnthropicLLMClient
                fallback_client = AnthropicLLMClient(self._fallback)
                return await fallback_client.complete(
                    system=system, messages=messages, max_tokens=max_tokens, model=model
                )
            raise RuntimeError("No SARVAM_API_KEY and no fallback client available")

        # Build combined messages (system + user messages)
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        import httpx
        from src.utils.retry import api_call_with_retry

        async def _call():
            async with httpx.AsyncClient(timeout=60.0) as http:
                resp = await http.post(
                    f"{self.SARVAM_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model or self.DEFAULT_MODEL,
                        "messages": all_messages,
                        "max_tokens": max_tokens,
                    },
                )
                if resp.status_code == 429:
                    # Create a mock exception with status_code for retry
                    err = Exception(f"Sarvam rate limit: {resp.status_code}")
                    err.status_code = 429  # type: ignore[attr-defined]
                    raise err
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]

        return await api_call_with_retry(_call)
