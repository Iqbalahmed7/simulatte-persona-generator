/**
 * ReferralLauncher — global modal trigger for the referral card.
 *
 * Mounted once in app/layout. Listens for window events
 *   window.dispatchEvent(new Event("open-referral"))
 * and pops a backdropped modal containing the existing ReferralCard.
 *
 * Lazy-fetches /api/me on first open so we don't waste a request on
 * every page load. Cached after first open for the rest of the session.
 *
 * Trigger sites:
 *   - NavRail "Invite a friend" button (desktop)
 *   - MobileBottomNav "Invite" tile (mobile)
 */
"use client";

import { useEffect, useState } from "react";
import ReferralCard from "./ReferralCard";

interface MeUser {
  personal_invite_code?: string | null;
}

export default function ReferralLauncher() {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetched, setFetched] = useState(false);

  // Listen for global "open-referral" events so any button anywhere
  // (NavRail, MobileBottomNav, future surfaces) can trigger us.
  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener("open-referral", onOpen);
    return () => window.removeEventListener("open-referral", onOpen);
  }, []);

  // Lazy-fetch the user's personal invite code on first open.
  useEffect(() => {
    if (!open || fetched) return;
    setLoading(true);
    fetch("/api/me", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((j: { user?: MeUser } | null) => {
        setCode(j?.user?.personal_invite_code ?? null);
        setFetched(true);
      })
      .catch(() => setFetched(true))
      .finally(() => setLoading(false));
  }, [open, fetched]);

  // Esc to close
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-0 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Invite a friend"
    >
      <button
        type="button"
        aria-label="Close"
        onClick={() => setOpen(false)}
        className="absolute inset-0 bg-void/85 backdrop-blur-sm"
      />
      <div
        className="relative w-full sm:max-w-lg bg-void border border-parchment/15 overflow-y-auto"
        style={{
          maxHeight: "min(90vh, calc(100vh - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px) - 32px))",
          paddingBottom: "env(safe-area-inset-bottom, 0px)",
        }}
      >
        <div className="flex items-start justify-between p-4 sm:p-5 border-b border-parchment/10 sticky top-0 bg-void z-10">
          <p className="text-[11px] font-mono text-signal uppercase tracking-[0.18em]">
            Invite
          </p>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close"
            className="text-parchment/60 hover:text-parchment p-1 -m-1"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        <div className="p-4 sm:p-5">
          {loading && !code && (
            <p className="font-mono text-[11px] text-static tracking-widest uppercase">
              Loading your link…
            </p>
          )}
          {!loading && !code && fetched && (
            <p className="text-parchment/72 text-sm">
              Couldn&#x2019;t load your invite link. Try refreshing the page.
            </p>
          )}
          {code && <ReferralCard code={code} />}
        </div>
      </div>
    </div>
  );
}

/** Convenience helper — call from anywhere to open the modal. */
export function openReferralModal() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("open-referral"));
  }
}
