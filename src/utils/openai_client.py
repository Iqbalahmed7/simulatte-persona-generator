"""openai_client.py — OpenAI provider implementing BaseLLMClient.

Adapter so OpenAI can be swapped in for low/medium-sensitivity stages.
NOT for use on locked stages (decide, synthesis) without passing the
calibration parity gate first — see provider_locks.py.

Default model is gpt-4o-mini (cheapest competent tier). Override per-call.
"""
from __future__ import annotations
import os
from typing import Any

from src.sarvam.llm_client import BaseLLMClient


class InsufficientCreditError(Exception):
    """Raised when the provider account is out of credits / quota."""


class OpenAILLMClient(BaseLLMClient):
    """OpenAI Chat Completions API wrapped to BaseLLMClient interface.

    Translates Anthropic-style (system, messages) → OpenAI chat format.
    """

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, client: Any | None = None) -> None:
        if client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise ImportError(
                    "openai package not installed — add `openai>=1.40` to requirements.txt"
                ) from e
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not api_key:
                raise ValueError("OPENAI_API_KEY env var not set")
            client = AsyncOpenAI(api_key=api_key)
        self._client = client

    @property
    def provider(self) -> str:
        return "openai"

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int = 1024,
        model: str | None = None,
    ) -> str:
        # OpenAI puts system in the messages array, not as a separate arg
        oai_messages = [{"role": "system", "content": system}, *messages]

        try:
            resp = await self._client.chat.completions.create(
                model=model or self.DEFAULT_MODEL,
                messages=oai_messages,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            # Normalise credit / quota errors so the router can failover
            msg = str(exc).lower()
            if any(s in msg for s in ("insufficient_quota", "billing", "exceeded")):
                raise InsufficientCreditError(str(exc)) from exc
            raise

        return resp.choices[0].message.content or ""
