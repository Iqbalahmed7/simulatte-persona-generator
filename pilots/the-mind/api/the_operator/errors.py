"""the_operator/errors.py — custom exceptions and error response helpers."""
from __future__ import annotations

from fastapi import HTTPException


def _err(code: str, detail: str, status: int, retryable: bool = False) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": code, "detail": detail, "retryable": retryable},
    )


def twin_not_found(twin_id: str) -> HTTPException:
    return _err("twin_not_found", f"Twin '{twin_id}' not found", 404)

def twin_already_exists(slug: str) -> HTTPException:
    return _err(
        "twin_already_exists",
        f"A Twin with slug '{slug}' already exists. Pass ?force=true to overwrite.",
        409,
    )

def operator_allowance_exceeded(action: str, used: int, limit: int, resets_at: str) -> HTTPException:
    return HTTPException(
        status_code=402,
        detail={
            "error": "operator_allowance_exceeded",
            "action": action,
            "used": used,
            "limit": limit,
            "resets_at": resets_at,
            "retryable": False,
        },
    )

def recon_failed(reason: str = "No public signals found") -> HTTPException:
    return _err("recon_failed", reason, 422)

def recon_budget_exceeded() -> HTTPException:
    return _err("recon_budget_exceeded", "Token budget exceeded during reconnaissance", 422)

def recon_unavailable() -> HTTPException:
    return _err("recon_unavailable", "Web search temporarily unavailable", 503, retryable=True)

def synthesis_failed() -> HTTPException:
    return _err("synthesis_failed", "Failed to synthesise Twin profile", 500)

def moderation_blocked() -> HTTPException:
    return _err("moderation_blocked", "Input was blocked by content moderation", 403)

def session_ended() -> HTTPException:
    return _err("session_ended", "This probe session has ended", 410)

def eu_subject_blocked() -> HTTPException:
    return _err(
        "eu_subject_blocked",
        "The Operator does not currently profile EU-based subjects (GDPR Phase 1 exclusion).",
        451,  # Unavailable For Legal Reasons
    )
