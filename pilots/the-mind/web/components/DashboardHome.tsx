/**
 * DashboardHome — the authed user's home view at /dashboard.
 *
 * Wrapped by <AppShell>: NavRail (CTAs + nav) on the left, WallTicker
 * (live community feed) on the right. Center column owns the user's
 * own status: greeting, weekly allowance, and their personas.
 *
 * The 2-personas-per-week constraint shapes the design: each persona
 * card is rich (probes / chats / expires-in) so users feel each
 * generation was earned.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "./AppShell";
import MobileActionGrid from "./MobileActionGrid";
import LivePersonaWall from "./LivePersonaWall";
import ReferralCard from "./ReferralCard";

interface MyPersona {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  occupation?: string;
  snippet?: string;
  portrait_url: string | null;
  probes_run: number;
  chats_had: number;
  expires_in_days: number;
  created_at: string | null;
}

interface MeAllowance {
  personas: { used: number; limit: number };
  probes:   { used: number; limit: number };
  chats:    { used: number; limit: number };
  resets_at: string;
}

interface MeUser {
  name: string | null;
  email: string;
  personal_invite_code?: string | null;
}

export default function DashboardHome({
  authToken,
  isAdmin = false,
}: {
  authToken: string;
  isAdmin?: boolean;
}) {
  const [user, setUser] = useState<MeUser | null>(null);
  const [allowance, setAllowance] = useState<MeAllowance | null>(null);
  const [personas, setPersonas] = useState<MyPersona[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    // Same-origin proxies — see /api/me and /api/me/personas. Cross-origin
    // fetches against the Railway API host get blocked by Brave Shields and
    // some content blockers.
    Promise.all([
      fetch("/api/me", { cache: "no-store" }).then(r => r.ok ? r.json() : null),
      fetch("/api/me/personas", { cache: "no-store" }).then(r => r.ok ? r.json() : []),
    ]).then(([me, ps]) => {
      if (cancelled) return;
      if (me) {
        setUser(me.user);
        setAllowance(me.allowance);
      }
      setPersonas(Array.isArray(ps) ? ps : []);
      setLoaded(true);
    }).catch(() => setLoaded(true));
    return () => { cancelled = true; };
  }, [authToken]);

  const first = (user?.name ?? "").split(" ")[0];
  const hasPersonas = personas.length > 0;
  const personasUsed = allowance?.personas.used ?? 0;
  const personasLimit = allowance?.personas.limit ?? 2;
  const personasLeft = Math.max(0, personasLimit - personasUsed);

  const navPersonas = personas.map((p) => ({
    persona_id: p.persona_id,
    name: p.name,
    age: p.age,
    city: p.city,
    country: p.country,
    occupation: p.occupation,
    snippet: p.snippet,
    portrait_url: p.portrait_url,
  }));

  return (
    <AppShell personas={navPersonas} personasLeft={personasLeft} isAdmin={isAdmin}>
      <div className="px-4 sm:px-8 lg:px-12 pt-6 sm:pt-12 pb-28 sm:pb-12 max-w-3xl mx-auto">
        {/* Greeting */}
        <section className="pb-6 sm:pb-8">
          <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-3">
            YOUR MIND
          </p>
          <h1
            className="font-condensed font-black text-parchment leading-[0.96] mb-3"
            style={{ fontSize: "clamp(32px, 4.5vw, 48px)", letterSpacing: "-0.008em" }}
          >
            {hasPersonas
              ? (first ? `Welcome back, ${first}.` : "Welcome back.")
              : (first ? `Welcome, ${first}.` : "Welcome to The Mind.")}
          </h1>
          <p className="text-parchment/72 text-base leading-[1.78] max-w-xl">
            {hasPersonas
              ? buildCopy(personasLeft)
              : `You have ${personasLimit} builds this week. Use one to bring your first person to life.`}
          </p>
        </section>

        {/* Mobile-only action grid — desktop has these in the NavRail */}
        <section className="md:hidden pb-8">
          <p className="text-[10px] font-mono text-static uppercase tracking-[0.18em] mb-3">
            Actions
          </p>
          <MobileActionGrid personas={navPersonas} personasLeft={personasLeft} />
        </section>

        {/* Refer-a-friend — prominent on mobile (the go-to screen for
            Simulatte). Sits above the allowance card so it's the first
            substantive content after the primary CTA grid. */}
        {user?.personal_invite_code && (
          <section className="pb-8">
            <ReferralCard code={user.personal_invite_code} />
          </section>
        )}

        {/* Allowance card — primary status block now that the action grid
            has moved into the NavRail (or the mobile grid above) */}
        <section className="pb-10">
          <AllowanceCard allowance={allowance} loaded={loaded} />
        </section>

        {/* Your personas */}
        {hasPersonas && (
          <section className="pb-4">
            <div className="flex items-baseline justify-between gap-4 mb-5">
              <h2 className="font-condensed font-bold text-parchment uppercase tracking-wider text-lg sm:text-xl">
                Your personas
              </h2>
              <span className="font-mono text-[10px] text-static tracking-widest uppercase">
                {personas.length} active
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {personas.map((p) => (
                <PersonaCard key={p.persona_id} p={p} />
              ))}
            </div>
          </section>
        )}

        {/* Mobile-only community wall — desktop has the right-rail ticker */}
        <section className="md:hidden mt-10 pt-8 border-t border-parchment/10">
          <div className="flex items-baseline justify-between gap-4 mb-4">
            <h2 className="font-condensed font-bold text-parchment uppercase tracking-wider text-lg">
              The wall
            </h2>
            <Link
              href="/community"
              className="font-mono text-[10px] text-static hover:text-signal tracking-widest uppercase"
            >
              See all →
            </Link>
          </div>
          <div className="relative h-[60vh] overflow-hidden border border-parchment/10">
            <LivePersonaWall />
          </div>
        </section>

        {/* Empty-state nudge for users with zero personas */}
        {loaded && !hasPersonas && (
          <section className="border border-parchment/10 p-6 sm:p-8">
            <p className="text-[11px] font-mono text-signal uppercase tracking-[0.18em] mb-4">
              Get started
            </p>
            <p className="text-parchment text-lg mb-2">
              Build your first synthetic person.
            </p>
            <p className="text-parchment/72 text-sm leading-relaxed mb-6">
              A paragraph is enough. Describe who they are — life, work, what they care
              about — and The Mind constructs a coherent person you can probe and chat with.
            </p>
            <Link
              href="/generate"
              className="inline-block bg-signal text-void font-condensed font-bold uppercase tracking-wider px-6 py-3"
            >
              Generate persona →
            </Link>
          </section>
        )}
      </div>
    </AppShell>
  );
}

function AllowanceCard({ allowance, loaded }: { allowance: MeAllowance | null; loaded: boolean }) {
  if (!loaded) {
    return (
      <div className="border border-parchment/10 p-5 sm:p-6">
        <p className="font-mono text-[10px] text-static tracking-widest uppercase">Loading…</p>
      </div>
    );
  }
  if (!allowance) {
    return (
      <div className="border border-parchment/10 p-5 sm:p-6">
        <p className="font-mono text-[10px] text-static tracking-widest uppercase">YOUR WEEK</p>
        <p className="text-parchment/60 text-sm mt-2">Couldn&#x2019;t load your allowance.</p>
      </div>
    );
  }
  return (
    <div className="border border-parchment/10 p-5 sm:p-6">
      <p className="font-mono text-[10px] text-static tracking-widest uppercase mb-4">YOUR WEEK</p>
      <div className="space-y-3">
        <AllowanceRow label="Personas" used={allowance.personas.used} limit={allowance.personas.limit} />
        <AllowanceRow label="Probes" used={allowance.probes.used} limit={allowance.probes.limit} />
        <AllowanceRow label="Chats" used={allowance.chats.used} limit={allowance.chats.limit} />
      </div>
      {allowance.resets_at && (
        <p className="font-mono text-[10px] text-parchment/40 tracking-widest uppercase mt-5 pt-4 border-t border-parchment/10">
          Resets {formatResets(allowance.resets_at)}
        </p>
      )}
    </div>
  );
}

function AllowanceRow({ label, used, limit }: { label: string; used: number; limit: number }) {
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="font-sans text-[13px] text-parchment/80">{label}</span>
        <span className="font-mono text-xs">
          <span className="text-signal">{used}</span>
          <span className="text-parchment/40"> / {limit}</span>
        </span>
      </div>
      <div className="h-1 bg-parchment/8">
        <div className="h-1 bg-signal" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function PersonaCard({ p }: { p: MyPersona }) {
  const place = [p.city, p.country].filter(Boolean).join(", ");
  const expiringSoon = p.expires_in_days <= 7;
  return (
    <Link
      href={`/persona/${p.persona_id}`}
      className="group border border-parchment/10 hover:border-signal/40 transition-colors flex flex-col"
    >
      <div className="relative" style={{ aspectRatio: "4 / 5" }}>
        {p.portrait_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={p.portrait_url}
            alt=""
            loading="lazy"
            className="absolute inset-0 w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
          />
        ) : (
          <div className="absolute inset-0 bg-parchment/[0.03] flex items-center justify-center">
            <span className="font-mono text-[10px] text-static tracking-widest uppercase">No portrait</span>
          </div>
        )}
      </div>
      <div className="p-3 sm:p-4 border-t border-parchment/10">
        <div className="font-condensed font-bold text-parchment text-base sm:text-lg leading-tight truncate">
          {p.name || "—"}
          {p.age ? <span className="text-parchment/60 font-normal">, {p.age}</span> : null}
        </div>
        {place && (
          <div className="font-mono text-[10px] text-static tracking-widest uppercase truncate mt-0.5">
            {place}
          </div>
        )}
        <div className="flex items-center gap-3 mt-3 font-mono text-[10px] text-parchment/60 tracking-widest uppercase">
          <span>{p.probes_run} probe{p.probes_run === 1 ? "" : "s"}</span>
          <span className="text-parchment/20">·</span>
          <span>{p.chats_had} chat{p.chats_had === 1 ? "" : "s"}</span>
        </div>
        <div className={
          "font-mono text-[10px] tracking-widest uppercase mt-2 " +
          (expiringSoon ? "text-amber-400/80" : "text-parchment/40")
        }>
          {p.expires_in_days <= 0
            ? "Expires today"
            : p.expires_in_days === 1
            ? "1 day to go"
            : `${p.expires_in_days} days to go`}
        </div>
      </div>
    </Link>
  );
}

function buildCopy(left: number): string {
  if (left === 0) return "You've used your two builds this week. Probe what you've got, or wait for the reset.";
  if (left === 1) return "One build left this week. Make it count.";
  return "Two builds at your disposal this week. Build one. Probe them.";
}

function formatResets(iso: string): string {
  try {
    const target = new Date(iso);
    const now = new Date();
    const diffDays = Math.max(0, Math.ceil((target.getTime() - now.getTime()) / 86400000));
    if (diffDays === 0) return "today";
    if (diffDays === 1) return "tomorrow";
    return `${target.toLocaleDateString(undefined, { weekday: "long" })} · ${diffDays} days away`;
  } catch {
    return "Monday";
  }
}
