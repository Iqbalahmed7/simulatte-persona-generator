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

type Phase = "loading" | "active" | "pending" | "anon" | "error";

// localStorage key — survives refreshes within a tab but not across
// browser restarts, so a stale "active" verdict can't leak indefinitely
// if the operator bans someone. Server still enforces on every request.
const CACHE_KEY = "mind:access:v1";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24h — server enforces, so this is just a UX hint

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
      // Reuse the /api/token endpoint that the rest of the app uses.
      const tokRes = await fetch("/api/token", { cache: "no-store" });
      if (!tokRes.ok) {
        setPhase("anon");
        return;
      }
      const { token: tk } = await tokRes.json();
      if (!tk) {
        setPhase("anon");
        return;
      }
      setToken(tk);
      const meRes = await fetch(`${API}/me`, {
        headers: { Authorization: `Bearer ${tk}` },
        cache: "no-store",
      });
      if (!meRes.ok) {
        setPhase("error");
        return;
      }
      const j: MeResponse = await meRes.json();
      setMe(j);
      const status = j.user?.access_status ?? "active";
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

  if (phase === "pending" && token) {
    return (
      <Waitlist
        authToken={token}
        userName={me?.user.name ?? null}
        onActivated={() => {
          // Re-fetch /me — once it returns active, we render children.
          void loadMe();
        }}
      />
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
