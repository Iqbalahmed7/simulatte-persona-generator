"""pilots/the-mind/api/auth.py — FastAPI auth middleware for The Mind.

Verifies Auth.js v5 JWTs, loads users from Postgres, and enforces
per-user ISO-week allowances.

Usage in main.py:
    from auth import get_current_user, check_and_increment_allowance
    from db import User

    @app.post("/generate-persona")
    async def generate(
        request: ICPRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        await check_and_increment_allowance(user, "persona", db)
        ...
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Literal

import jwt
from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import Allowance, Event, EventType, InviteCode, LIMITS, User, get_db

# ── Helpers ───────────────────────────────────────────────────────────────

_CALENDLY = "https://calendly.com/iqbal-simulatte"

ACTION_LIMIT = {
    "persona": LIMITS["persona"],
    "probe": LIMITS["probe"],
    "chat": LIMITS["chat"],
}

ACTION_FIELD = {
    "persona": "personas_used",
    "probe": "probes_used",
    "chat": "chats_used",
}

ACTION_EVENT_TYPE = {
    "persona": EventType.persona_generated,
    "probe": EventType.probe_run,
    "chat": EventType.chat_message,
}


def _iso_week_monday(dt: datetime) -> date:
    """Return the Monday of the ISO week containing dt."""
    d = dt.date()
    return d - __import__("datetime").timedelta(days=d.weekday())


def _next_monday(week_start: date) -> datetime:
    """ISO-week reset time: next Monday 00:00 UTC."""
    next_mon = week_start + __import__("datetime").timedelta(days=7)
    return datetime(next_mon.year, next_mon.month, next_mon.day, tzinfo=timezone.utc)


# ── JWT verification ──────────────────────────────────────────────────────

def _get_nextauth_secret() -> str:
    secret = os.environ.get("NEXTAUTH_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="NEXTAUTH_SECRET not configured on server")
    return secret


def _decode_token(token: str) -> dict:
    """Decode and verify an Auth.js v5 JWT.

    Auth.js v5 uses HS256 by default with NEXTAUTH_SECRET as the signing key.
    The payload contains `sub` (user ID) and optionally `email`.
    """
    secret = _get_nextauth_secret()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired — please sign in again")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid session token: {exc}")


# ── FastAPI dependency: get_current_user ──────────────────────────────────

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract Auth.js session JWT from Authorization: Bearer header or cookie.

    Verifies the JWT with NEXTAUTH_SECRET, then looks up the user in Postgres.
    Raises HTTP 401 if the token is missing, invalid, or the user doesn't exist.
    """
    token: str | None = None

    # 1. Check Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]

    # 2. Fall back to Auth.js session cookie
    if not token:
        # Auth.js v5 default cookie names
        for cookie_name in (
            "authjs.session-token",
            "__Secure-authjs.session-token",
            "next-auth.session-token",
            "__Secure-next-auth.session-token",
        ):
            token = request.cookies.get(cookie_name)
            if token:
                break

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated — sign in at mind.simulatte.io/sign-in",
        )

    payload = _decode_token(token)

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        # User may exist by email if the JWT carries it
        email: str | None = payload.get("email")
        if email:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found — your session may be stale, please sign in again",
        )

    # Backfill invite_code_used from the `invite_ok` cookie on first authed
    # call. Atomically increments the matching InviteCode.used_count so
    # admins can see redemption velocity per channel.
    if not getattr(user, "invite_code_used", None):
        invite_cookie = request.cookies.get("invite_ok") or ""
        norm = invite_cookie.strip().upper()
        if norm:
            try:
                from sqlalchemy import update as _upd
                ic = (await db.execute(
                    select(InviteCode).where(InviteCode.code == norm)
                )).scalar_one_or_none()
                if ic is not None and bool(getattr(ic, "active", True)):
                    user.invite_code_used = norm
                    await db.execute(
                        _upd(InviteCode)
                        .where(InviteCode.code == norm)
                        .values(used_count=(InviteCode.used_count + 1))
                    )
                    await db.commit()
            except Exception:
                # Never block auth on backfill — schema may not yet exist
                # in some environments.
                await db.rollback()

    # Banned users: refuse all gated actions. 403 (not 401) so the client
    # doesn't try to re-auth — the ban will follow them. Admins (by env var)
    # are exempt — they need access to lift bans.
    if getattr(user, "banned", False):
        admin_emails = {
            e.strip().lower()
            for e in (os.environ.get("ADMIN_EMAILS", "") or "").split(",")
            if e.strip()
        }
        if (user.email or "").lower() not in admin_emails:
            reason = getattr(user, "banned_reason", None) or "violation of usage policy"
            raise HTTPException(
                status_code=403,
                detail=f"Your account has been suspended ({reason}). Contact mind@simulatte.io if you believe this is in error.",
            )

    return user


# ── FastAPI dependency: check_and_increment_allowance ────────────────────

async def check_and_increment_allowance(
    user: User,
    action: Literal["persona", "probe", "chat"],
    db: AsyncSession,
) -> None:
    """Check the user's ISO-week allowance for action.

    - Creates the allowances row if it doesn't exist for the current week.
    - Admin emails (in ADMIN_EMAILS env var) bypass the limit entirely
      so the operator can dogfood without hitting their own paywall.
    - If the user is at or over the limit, raises HTTP 402 with a structured
      payload so the frontend can show the hard-wall modal.
    - Otherwise increments the counter and logs an event.
    """
    # Admin bypass — admins still get the event logged but no quota check.
    admin_emails = {
        e.strip().lower()
        for e in (os.environ.get("ADMIN_EMAILS", "") or "").split(",")
        if e.strip()
    }
    is_admin = (user.email or "").lower() in admin_emails

    now = datetime.now(timezone.utc)
    week_start = _iso_week_monday(now)
    limit = ACTION_LIMIT[action]
    field = ACTION_FIELD[action]

    # Load or create allowance row for this week
    result = await db.execute(
        select(Allowance).where(
            Allowance.user_id == user.id,
            Allowance.week_starting == week_start,
        )
    )
    allowance = result.scalar_one_or_none()

    if allowance is None:
        allowance = Allowance(
            user_id=user.id,
            week_starting=week_start,
            personas_used=0,
            probes_used=0,
            chats_used=0,
        )
        db.add(allowance)
        await db.flush()  # assigns defaults without committing

    used: int = getattr(allowance, field)

    if used >= limit and not is_admin:
        resets_at = _next_monday(week_start)
        raise HTTPException(
            status_code=402,
            detail={
                "error": "allowance_exceeded",
                "action": action,
                "used": used,
                "limit": limit,
                "resets_at": resets_at.isoformat(),
                "upgrade_url": _CALENDLY,
            },
        )

    # Increment counter
    setattr(allowance, field, used + 1)
    allowance.updated_at = now

    # Log event
    db.add(Event(
        user_id=user.id,
        type=ACTION_EVENT_TYPE[action],
        ref_id=None,  # caller can update ref_id after the action completes
        created_at=now,
    ))

    await db.commit()


# ── /me response builder ──────────────────────────────────────────────────

async def build_me_response(user: User, db: AsyncSession) -> dict:
    """Build the /me payload: user info + current week's allowance state."""
    now = datetime.now(timezone.utc)
    week_start = _iso_week_monday(now)
    resets_at = _next_monday(week_start)

    result = await db.execute(
        select(Allowance).where(
            Allowance.user_id == user.id,
            Allowance.week_starting == week_start,
        )
    )
    allowance = result.scalar_one_or_none()

    personas_used = allowance.personas_used if allowance else 0
    probes_used = allowance.probes_used if allowance else 0
    chats_used = allowance.chats_used if allowance else 0

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "image": user.image,
        },
        "allowance": {
            "personas": {
                "used": personas_used,
                "limit": LIMITS["persona"],
            },
            "probes": {
                "used": probes_used,
                "limit": LIMITS["probe"],
            },
            "chats": {
                "used": chats_used,
                "limit": LIMITS["chat"],
            },
            "resets_at": resets_at.isoformat(),
        },
    }
