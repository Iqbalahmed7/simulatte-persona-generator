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


# ── Code generation helpers ──────────────────────────────────────────────

# URL-safe alphabet (no I/l/0/O confusion). 10 chars → ~52 bits of entropy.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def mint_random_code(length: int = 10) -> str:
    """Random URL-safe invite code, e.g. 'XK7MP9ABCD'. Uppercase only so
    redemption matches the existing `.upper()` normalisation."""
    import secrets
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


async def _create_personal_invite_code(db: AsyncSession, user: User) -> str:
    """Mint a fresh personal reshare code for a newly-activated user, and
    INSERT the matching InviteCode row so future redemptions resolve.

    Tries up to 5 times to avoid the (extremely unlikely) collision; if
    it still collides, returns the last attempted code anyway — caller
    will surface the rollback.
    """
    for _ in range(5):
        candidate = mint_random_code(10)
        existing = (await db.execute(
            select(InviteCode).where(InviteCode.code == candidate)
        )).scalar_one_or_none()
        if existing is None:
            db.add(InviteCode(
                code=candidate,
                label=None,
                max_uses=None,             # unlimited; tree is the control
                used_count=0,
                active=True,
                created_by_user_id=user.id,
                created_by_email=user.email,
            ))
            await db.flush()
            return candidate
    return candidate  # noqa: F821 — pragma: improbable

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

    # Admin auto-bypass: admins are always treated as active. They got
    # `pending` only because the column default tagged them retroactively
    # — flip them to active on first authed call so they never see the
    # waitlist screen and can never be locked out of their own admin tools.
    admin_emails_set = {
        e.strip().lower()
        for e in (os.environ.get("ADMIN_EMAILS", "") or "").split(",")
        if e.strip()
    }
    if (user.email or "").lower() in admin_emails_set:
        if (getattr(user, "access_status", "active") or "active") != "active":
            user.access_status = "active"
            user.approved_at = datetime.now(timezone.utc)
            try:
                if not getattr(user, "personal_invite_code", None):
                    user.personal_invite_code = await _create_personal_invite_code(db, user)
                await db.commit()
            except Exception:
                await db.rollback()

    # Activation pipeline. Two responsibilities, run together so the
    # commit is atomic:
    #   1. Backfill invite_code_used from the `invite_ok` cookie if it's
    #      set and we haven't recorded a code for this user yet.
    #   2. If the user is `pending` and a valid invite cookie is present,
    #      flip them to `active`, mint a personal_invite_code (their own
    #      reshare code), and record invited_by_user_id from the
    #      redeemed code so the referral tree is populated.
    is_pending = (getattr(user, "access_status", "active") or "active") == "pending"
    needs_backfill = not getattr(user, "invite_code_used", None)
    if is_pending or needs_backfill:
        invite_cookie = request.cookies.get("invite_ok") or ""
        norm = invite_cookie.strip().upper()
        if norm:
            try:
                from sqlalchemy import update as _upd
                ic = (await db.execute(
                    select(InviteCode).where(InviteCode.code == norm)
                )).scalar_one_or_none()
                if ic is not None and bool(getattr(ic, "active", True)):
                    # Capacity check — exhausted codes don't activate.
                    max_uses = getattr(ic, "max_uses", None)
                    used = int(getattr(ic, "used_count", 0) or 0)
                    if max_uses is None or used < max_uses:
                        if needs_backfill:
                            user.invite_code_used = norm
                        if is_pending:
                            user.access_status = "active"
                            user.approved_at = datetime.now(timezone.utc)
                            user.invited_by_user_id = getattr(ic, "created_by_user_id", None)
                            if not getattr(user, "personal_invite_code", None):
                                personal = await _create_personal_invite_code(db, user)
                                user.personal_invite_code = personal
                        await db.execute(
                            _upd(InviteCode)
                            .where(InviteCode.code == norm)
                            .values(used_count=(InviteCode.used_count + 1))
                        )
                        await db.commit()
                        is_pending = False  # avoid the gate below
            except Exception:
                await db.rollback()

    # Pending gate: organic users who haven't redeemed a code can hit
    # /me, /redeem-code, /access-requests, and /sign-out — but every
    # other authed endpoint returns 403 access_pending so the frontend
    # can render the waitlist screen instead of the app.
    if is_pending:
        path = request.url.path or ""
        pending_allowed = (
            path.endswith("/me")
            or path.endswith("/redeem-code")
            or path.endswith("/access-requests")
            or path.endswith("/access-requests/mine")
        )
        if not pending_allowed:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "access_pending",
                    "message": "Your account is on the waitlist. Redeem an invite code or wait for approval.",
                },
            )

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
    # Admin bypass — admins skip allowance entirely (no quota check, no
    # counter increment, no event log). They can dogfood without using
    # their own limits. Their generations are still discoverable via
    # /me/personas because that endpoint also looks at Event rows with
    # null ref_id (see _log_persona_event below).
    admin_emails = {
        e.strip().lower()
        for e in (os.environ.get("ADMIN_EMAILS", "") or "").split(",")
        if e.strip()
    }
    is_admin = (user.email or "").lower() in admin_emails
    if is_admin:
        # Still log the event so admins show up in audit reports — but
        # no allowance row, no quota check.
        db.add(Event(
            user_id=user.id,
            type=ACTION_EVENT_TYPE[action],
            ref_id=None,
            created_at=datetime.now(timezone.utc),
        ))
        await db.commit()
        return

    now = datetime.now(timezone.utc)
    week_start = _iso_week_monday(now)
    # Per-user override takes precedence; fall back to global LIMITS.
    _override_col = {"persona": "persona_limit_override", "probe": "probe_limit_override", "chat": "chat_limit_override"}[action]
    limit = getattr(user, _override_col, None) or ACTION_LIMIT[action]
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

    # Admin override — operator should see 0/<huge> in the dashboard so
    # the frontend Generate tile / Probe / Chat actions stay enabled
    # regardless of any stale Allowance row from before the bypass landed.
    admin_emails = {
        e.strip().lower()
        for e in (os.environ.get("ADMIN_EMAILS", "") or "").split(",")
        if e.strip()
    }
    is_admin_user = (user.email or "").lower() in admin_emails
    if is_admin_user:
        personas_used = 0
        probes_used = 0
        chats_used = 0

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "image": user.image,
            "access_status": getattr(user, "access_status", "active"),
            "personal_invite_code": getattr(user, "personal_invite_code", None),
            "invited_by_user_id": getattr(user, "invited_by_user_id", None),
        },
        "allowance": {
            "personas": {
                "used": personas_used,
                "limit": getattr(user, "persona_limit_override", None) or LIMITS["persona"],
            },
            "probes": {
                "used": probes_used,
                "limit": getattr(user, "probe_limit_override", None) or LIMITS["probe"],
            },
            "chats": {
                "used": chats_used,
                "limit": getattr(user, "chat_limit_override", None) or LIMITS["chat"],
            },
            "resets_at": resets_at.isoformat(),
        },
    }
