"""API key auth dependency for /v1/* endpoints."""
from __future__ import annotations

import os

from fastapi import Header, HTTPException, status


def require_api_key(
    authorization: str | None = Header(default=None),
    x_internal_api_key: str | None = Header(default=None, alias="X-Internal-Api-Key"),
) -> str:
    """Accepts `Authorization: Bearer <key>` or `X-Internal-Api-Key: <key>`.

    The expected key is read from INTERNAL_API_KEY env var. If unset, auth is
    disabled (useful in local dev). In production, INTERNAL_API_KEY MUST be set.
    """
    expected = os.environ.get("INTERNAL_API_KEY", "").strip()
    if not expected:
        # Dev mode — auth disabled
        return "anonymous"

    presented: str | None = None
    if authorization:
        parts = authorization.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            presented = parts[1].strip()
    if not presented and x_internal_api_key:
        presented = x_internal_api_key.strip()

    if not presented or presented != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return presented
