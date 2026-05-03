"""the_operator/allowance.py — allowance enforcement for Operator actions.

Mirrors auth.check_and_increment_allowance but uses operator_allowances table.
Admin emails (ADMIN_EMAILS env var) bypass entirely.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from the_operator.config import OPERATOR_LIMITS
from the_operator.errors import operator_allowance_exceeded
from the_operator.models import OperatorAllowance

OperatorAction = Literal["twin_build", "twin_refresh", "probe_message", "frame_score"]

_SERVICE_USER_ID = "service-operator"  # X-API-Key callers (Trinity pipeline) — always bypass

_FIELD_MAP: dict[OperatorAction, str] = {
    "twin_build":    "twins_built",
    "twin_refresh":  "twin_refreshes",
    "probe_message": "probe_messages",
    "frame_score":   "frame_scores",
}


def _iso_week_monday(dt: datetime) -> date:
    return (dt.date() - timedelta(days=dt.weekday()))


def _next_monday(week_start: date) -> date:
    return week_start + timedelta(days=7)


def _admin_emails() -> set[str]:
    return {
        e.strip().lower()
        for e in (os.environ.get("ADMIN_EMAILS", "") or "").split(",")
        if e.strip()
    }


async def check_and_increment_operator_allowance(
    user,                     # db.User — typed loosely to avoid circular import
    action: OperatorAction,
    db: AsyncSession,
) -> None:
    """Raise HTTP 402 if the user is at their weekly limit, else increment.

    Admins bypass entirely — no row created, no counter incremented.
    """
    is_admin = (user.email or "").lower() in _admin_emails()
    is_service = getattr(user, "id", None) == _SERVICE_USER_ID
    if is_admin or is_service:
        return

    now = datetime.now(timezone.utc)
    week_start = _iso_week_monday(now)
    limit = OPERATOR_LIMITS[action]
    field = _FIELD_MAP[action]

    result = await db.execute(
        select(OperatorAllowance).where(
            OperatorAllowance.user_id == user.id,
            OperatorAllowance.week_starting == week_start,
        )
    )
    allowance = result.scalar_one_or_none()

    if allowance is None:
        allowance = OperatorAllowance(
            user_id=user.id,
            week_starting=week_start,
        )
        db.add(allowance)
        await db.flush()

    used: int = getattr(allowance, field)

    if used >= limit:
        resets_at = _next_monday(week_start)
        raise operator_allowance_exceeded(
            action=action,
            used=used,
            limit=limit,
            resets_at=resets_at.isoformat(),
        )

    setattr(allowance, field, used + 1)
    allowance.updated_at = now
    await db.commit()


async def get_operator_allowance_state(user, db: AsyncSession) -> dict:
    """Return the current week's allowance state for /operator/me."""
    now = datetime.now(timezone.utc)
    week_start = _iso_week_monday(now)
    resets_at  = _next_monday(week_start)

    is_admin = (user.email or "").lower() in _admin_emails()
    is_service = getattr(user, "id", None) == _SERVICE_USER_ID

    result = await db.execute(
        select(OperatorAllowance).where(
            OperatorAllowance.user_id == user.id,
            OperatorAllowance.week_starting == week_start,
        )
    )
    allowance = result.scalar_one_or_none()

    if is_admin or is_service or allowance is None:
        zeros = {"twins_built": 0, "twin_refreshes": 0, "probe_messages": 0, "frame_scores": 0}
        row = zeros
    else:
        row = {
            "twins_built":    allowance.twins_built,
            "twin_refreshes": allowance.twin_refreshes,
            "probe_messages": allowance.probe_messages,
            "frame_scores":   allowance.frame_scores,
        }

    inf = 9999 if (is_admin or is_service) else None

    return {
        "twin_build":    {"used": row["twins_built"],    "limit": inf or OPERATOR_LIMITS["twin_build"]},
        "twin_refresh":  {"used": row["twin_refreshes"], "limit": inf or OPERATOR_LIMITS["twin_refresh"]},
        "probe_message": {"used": row["probe_messages"], "limit": inf or OPERATOR_LIMITS["probe_message"]},
        "frame_score":   {"used": row["frame_scores"],   "limit": inf or OPERATOR_LIMITS["frame_score"]},
        "resets_at": resets_at.isoformat(),
    }
