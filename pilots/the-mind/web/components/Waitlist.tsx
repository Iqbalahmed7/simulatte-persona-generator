/**
 * Waitlist — shown to authenticated users whose access_status is
 * "pending". Two paths to escape:
 *   1. Paste an invite code (auto-activate via /redeem-code)
 *   2. Submit a "tell us why" reason (admin reviews + emails them in)
 *
 * Once status flips to active, the parent re-fetches /me and unmounts
 * this component, revealing the app underneath.
 */
"use client";

import { useEffect, useState } from "react";
import { API } from "@/lib/api";

/** Sign out via Auth.js's CSRF-protected POST endpoint. We avoid
 *  next-auth/react's signOut helper because it depends on
 *  SessionProvider, which isn't wired in the root layout. */
async function doSignOut() {
  try {
    const csrfRes = await fetch("/api/auth/csrf", { cache: "no-store" });
    const { csrfToken } = await csrfRes.json();
    const form = new FormData();
    form.append("csrfToken", csrfToken);
    form.append("callbackUrl", "/welcome");
    await fetch("/api/auth/signout", { method: "POST", body: form });
  } finally {
    window.location.href = "/welcome";
  }
}

interface ExistingRequest {
  exists: boolean;
  status?: string;
  reason?: string | null;
  created_at?: string | null;
}

export default function Waitlist({
  authToken,
  onActivated,
  userName,
}: {
  authToken: string;
  onActivated: () => void;
  userName?: string | null;
}) {
  const [code, setCode] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [existing, setExisting] = useState<ExistingRequest | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/access-requests/mine`, {
      headers: { Authorization: `Bearer ${authToken}` },
      cache: "no-store",
    })
      .then((r) => (r.ok ? r.json() : { exists: false }))
      .then((data) => {
        if (!cancelled) setExisting(data);
      })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [authToken]);

  async function onRedeem(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch(`${API}/redeem-code`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ code: code.trim().toUpperCase() }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        const detail = j.detail;
        const msg = (typeof detail === "string"
          ? detail
          : (detail as { message?: string })?.message) ?? "Code wasn't valid.";
        throw new Error(msg);
      }
      onActivated();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onRequest(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch(`${API}/access-requests`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ reason: reason.trim() || null }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || "Couldn't submit request");
      }
      // Refresh the existing-request snapshot
      const ar = await fetch(`${API}/access-requests/mine`, {
        headers: { Authorization: `Bearer ${authToken}` },
        cache: "no-store",
      }).then((r) => (r.ok ? r.json() : { exists: false }));
      setExisting(ar);
      setReason("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const first = (userName ?? "").split(" ")[0];

  return (
    <div className="min-h-screen bg-void text-parchment flex flex-col">
      <header className="border-b border-parchment/10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <span className="font-condensed font-black text-lg uppercase tracking-wider">
            The Mind
            <span className="ml-2 text-[10px] font-mono text-parchment/40 tracking-[0.18em]">
              BY SIMULATTE
            </span>
          </span>
          <button
            onClick={() => doSignOut()}
            className="text-[10px] font-mono text-parchment/60 hover:text-signal tracking-[0.18em] uppercase"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 py-12 sm:py-16">
        <div className="w-full text-center" style={{ maxWidth: "560px" }}>
          {/* Eyebrow + heading + subtitle — all centred */}
          <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-4">
            WAITLIST
          </p>
          <h1
            className="font-condensed font-black leading-[0.96] mb-5 mx-auto"
            style={{ fontSize: "clamp(34px, 6vw, 52px)", maxWidth: "14ch" }}
          >
            {first ? `${first}, you're on the list.` : "You're on the list."}
          </h1>
          <p
            className="text-parchment/72 leading-[1.78] mb-10 mx-auto"
            style={{ fontSize: "16px", maxWidth: "440px" }}
          >
            The Mind is in private launch. Paste an invite code from a friend,
            or tell us what you&#x2019;d like to test.
          </p>

          {/* — Redeem code (compact card, content left-aligned within) — */}
          <div className="border border-parchment/10 p-5 sm:p-6 mb-4 text-left">
            <p className="text-[11px] font-mono text-signal uppercase tracking-[0.18em] mb-3 text-center">
              I HAVE AN INVITE CODE
            </p>
            <form onSubmit={onRedeem} className="flex flex-col sm:flex-row gap-2 sm:gap-3">
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="INVITE CODE"
                className="flex-1 bg-transparent border border-parchment/20 px-4 py-3 font-mono text-sm tracking-widest focus:border-signal focus:outline-none text-center sm:text-left"
                autoComplete="off"
                spellCheck={false}
              />
              <button
                type="submit"
                disabled={busy || !code.trim()}
                className="bg-signal text-void font-condensed font-bold uppercase tracking-wider px-6 py-3 disabled:opacity-50"
              >
                {busy ? "Redeeming…" : "Redeem"}
              </button>
            </form>
          </div>

          {/* — Request access — */}
          <div className="border border-parchment/10 p-5 sm:p-6 text-left">
            <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-3 text-center">
              OR TELL US WHY YOU&#x2019;D LIKE ACCESS
            </p>
            {existing?.exists ? (
              <div className="text-center">
                <p className="text-parchment/80 mb-2">
                  We received your request
                  {existing.created_at
                    ? ` on ${new Date(existing.created_at).toLocaleDateString()}`
                    : ""}.
                </p>
                <p className="text-parchment/60 text-sm">
                  We&#x2019;ll email you when we&#x2019;ve approved you. In the
                  meantime, an invite link from a friend gets you in immediately.
                </p>
                {existing.reason && (
                  <blockquote className="mt-4 pl-4 border-l-2 border-parchment/20 text-parchment/60 text-sm italic text-left">
                    {existing.reason}
                  </blockquote>
                )}
              </div>
            ) : (
              <form onSubmit={onRequest} className="flex flex-col items-center gap-3">
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="One or two lines: who you'd build a persona of, or what you'd test."
                  rows={3}
                  maxLength={2000}
                  className="w-full bg-transparent border border-parchment/20 px-4 py-3 text-sm focus:border-signal focus:outline-none resize-none"
                />
                <button
                  type="submit"
                  disabled={busy}
                  className="border border-parchment/30 text-parchment font-condensed font-bold uppercase tracking-wider px-6 py-3 disabled:opacity-50 hover:bg-parchment/5"
                >
                  {busy ? "Sending…" : "Request access"}
                </button>
              </form>
            )}
          </div>

          {err && (
            <p className="mt-4 text-amber-400 text-sm font-mono">{err}</p>
          )}
        </div>
      </main>
    </div>
  );
}
