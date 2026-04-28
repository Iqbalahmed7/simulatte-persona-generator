/**
 * AccessGate — wrap any client-side page that requires access_status="active".
 *
 * Fetches /me with the backend HS256 token; if the user is pending,
 * renders the Waitlist screen instead of the children. Active users
 * see the children unchanged.
 *
 * Mount this on /generate, /persona/[id]/probe, and any future gated
 * page so pending users get a friendly waitlist instead of a 403 mid-flow.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { API } from "@/lib/api";
import Waitlist from "./Waitlist";

interface MeResponse {
  user: {
    id: string;
    email: string;
    name: string | null;
    image: string | null;
    access_status: "pending" | "active" | "banned";
    personal_invite_code: string | null;
  };
}

type Phase = "loading" | "active" | "pending" | "anon" | "error" | "banned";

// localStorage key — survives refreshes within a tab so a returning user
// doesn't see the "Checking access…" flicker. Server still enforces on
// every request. TTL kept short (30 min) so a banned user doesn't get to
// see the app shell for hours after the operator flips their flag.
const CACHE_KEY = "mind:access:v1";
const CACHE_TTL_MS = 30 * 60 * 1000;

function readCache(): "active" | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { status: string; ts: number };
    if (parsed.status !== "active") return null;
    if (Date.now() - parsed.ts > CACHE_TTL_MS) return null;
    return "active";
  } catch { return null; }
}

function writeCache(status: "active" | "pending") {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ status, ts: Date.now() }));
  } catch { /* ignore quota errors */ }
}

export default function AccessGate({ children }: { children: React.ReactNode }) {
  // Optimistic: if we've seen "active" within the TTL, render children
  // immediately and revalidate in the background. Eliminates the
  // "Checking access…" flicker on every refresh for the common case.
  const [phase, setPhase] = useState<Phase>(() => readCache() ? "active" : "loading");
  const [me, setMe] = useState<MeResponse | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const lastChecked = useRef<number>(0);

  async function loadMe() {
    try {
      // Same-origin proxy — Brave Shields and similar content blockers
      // can silently drop cross-origin fetches to the FastAPI host. The
      // /api/me Route Handler reads the Auth.js session server-side and
      // forwards the call. We still need a token for the Waitlist's
      // legacy callsites that haven't been switched yet, so fetch
      // /api/token in parallel.
      const [meRes, tokRes] = await Promise.all([
        fetch("/api/me", { cache: "no-store" }),
        fetch("/api/token", { cache: "no-store" }),
      ]);
      if (meRes.status === 401 || tokRes.status === 401) {
        setPhase("anon");
        return;
      }
      if (tokRes.ok) {
        const { token: tk } = await tokRes.json();
        if (tk) setToken(tk);
      }
      if (!meRes.ok) {
        setPhase("error");
        return;
      }
      const j: MeResponse = await meRes.json();
      setMe(j);
      let status = j.user?.access_status ?? "active";

      // Banned: invalidate cache, surface a dedicated screen — server
      // 403s would otherwise leave the user staring at a half-broken
      // app shell.
      if (status === "banned") {
        try { localStorage.removeItem(CACHE_KEY); } catch {}
        setPhase("banned");
        return;
      }

      // Pending + we have an invite_ok cookie or localStorage backup?
      // Redeem inline before flipping to the Waitlist UI — otherwise
      // the user sees a brief Waitlist flash while Waitlist's own
      // useEffect catches up. We CLEAR the cookie/localStorage BEFORE
      // the POST so a Waitlist that mounts in parallel can't double-
      // redeem and over-count an invite.
      if (status === "pending" && typeof document !== "undefined") {
        const cookieMatch = document.cookie.match(/(?:^|;\s*)invite_ok=([^;]+)/);
        const cookieCode = cookieMatch ? decodeURIComponent(cookieMatch[1]).trim().toUpperCase() : "";
        let lsCode = "";
        try { lsCode = (localStorage.getItem("invite_ok") || "").trim().toUpperCase(); } catch {}
        const candidate = cookieCode || lsCode;
        if (candidate) {
          // Clear FIRST — race-guard against Waitlist's own auto-redeem.
          document.cookie = "invite_ok=; Max-Age=0; path=/";
          try { localStorage.removeItem("invite_ok"); } catch {}
          try {
            const r = await fetch("/api/redeem-code", {
              method: "POST",
              headers: { "content-type": "application/json" },
              body: JSON.stringify({ code: candidate }),
            });
            if (r.ok) {
              // Re-fetch /me — it should now report active.
              const meRes2 = await fetch("/api/me", { cache: "no-store" });
              if (meRes2.ok) {
                const j2: MeResponse = await meRes2.json();
                setMe(j2);
                status = j2.user?.access_status ?? "active";
                if (status === "banned") {
                  try { localStorage.removeItem(CACHE_KEY); } catch {}
                  setPhase("banned");
                  return;
                }
              }
            }
          } catch { /* fall through to Waitlist */ }
        }
      }

      setPhase(status === "pending" ? "pending" : "active");
      writeCache(status === "pending" ? "pending" : "active");
      lastChecked.current = Date.now();
    } catch {
      setPhase("error");
    }
  }

  useEffect(() => {
    void loadMe();
  }, []);

  // No "Checking access…" screen. Render children optimistically while
  // /me is in flight; the server enforces access on every API call so a
  // pending user can't actually do anything sensitive. If /me comes back
  // pending, we flip to the Waitlist below.
  if (phase === "loading") {
    return <>{children}</>;
  }

  if (phase === "anon") {
    // Middleware should have caught this, but just in case — bounce to /welcome.
    if (typeof window !== "undefined") {
      window.location.href = "/welcome";
    }
    return null;
  }

  if (phase === "pending") {
    // Don't gate Waitlist behind a non-null token — the legacy redeem
    // and access-request endpoints have been switched to same-origin
    // proxies that read the session server-side, so authToken is no
    // longer required. Falling back to "" keeps types happy.
    return (
      <Waitlist
        authToken={token ?? ""}
        userName={me?.user.name ?? null}
        onActivated={() => {
          // Re-fetch /me — once it returns active, we render children.
          void loadMe();
        }}
      />
    );
  }

  if (phase === "banned") {
    return (
      <div className="min-h-screen bg-void text-parchment flex items-center justify-center px-6">
        <div className="max-w-md text-center">
          <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-3">
            ACCOUNT SUSPENDED
          </p>
          <h1 className="font-condensed font-black text-3xl mb-4 leading-tight">
            This account isn&#x2019;t active.
          </h1>
          <p className="text-parchment/72 mb-6">
            If you think this is a mistake, email{" "}
            <a href="mailto:mind@simulatte.io" className="text-signal hover:underline">
              mind@simulatte.io
            </a>{" "}
            and we&#x2019;ll take a look.
          </p>
        </div>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="min-h-screen bg-void text-parchment flex items-center justify-center px-6">
        <div className="max-w-md text-center">
          <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-3">
            COULDN&#x2019;T REACH THE SERVER
          </p>
          <p className="text-parchment/72 mb-6">
            Try refreshing. If this keeps happening, email
            mind@simulatte.io.
          </p>
          <button
            onClick={() => loadMe()}
            className="bg-signal text-void font-condensed font-bold uppercase tracking-wider px-6 py-3"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
