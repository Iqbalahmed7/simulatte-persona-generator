/**
 * DashboardHome — the authed user's home view at /dashboard.
 *
 * Three stacked sections (mobile-first):
 *   1. Greeting + weekly allowance card + Build CTA
 *   2. Your personas — rich horizontal-scroll cards (or grid on lg)
 *   3. Community wall — compact drift below
 *
 * The 2-personas-per-week constraint shapes the design: each persona
 * card is rich (probes / chats / expires-in) so users feel each
 * generation was earned, not a thumbnail in a sea.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { API } from "@/lib/api";
import LivePersonaWall from "./LivePersonaWall";

interface MyPersona {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
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
}

export default function DashboardHome({
  authToken,
}: {
  authToken: string;
}) {
  const [user, setUser] = useState<MeUser | null>(null);
  const [allowance, setAllowance] = useState<MeAllowance | null>(null);
  const [personas, setPersonas] = useState<MyPersona[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`${API}/me`, { headers: { Authorization: `Bearer ${authToken}` }, cache: "no-store" }).then(r => r.ok ? r.json() : null),
      fetch(`${API}/me/personas`, { headers: { Authorization: `Bearer ${authToken}` }, cache: "no-store" }).then(r => r.ok ? r.json() : []),
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

  return (
    <div className="bg-void text-parchment min-h-screen">
      {/* ── 1. GREETING + ALLOWANCE ───────────────────────────── */}
      <section className="px-4 sm:px-6 lg:px-14 pt-10 sm:pt-14 pb-10">
        <div className="max-w-7xl mx-auto">
          <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-3">
            YOUR MIND
          </p>
          <h1
            className="font-condensed font-black text-parchment leading-[0.96] mb-4"
            style={{ fontSize: "clamp(34px, 5.5vw, 56px)", letterSpacing: "-0.008em" }}
          >
            {hasPersonas
              ? (first ? `Welcome back, ${first}.` : "Welcome back.")
              : (first ? `Welcome, ${first}.` : "Welcome to The Mind.")}
          </h1>
          <p className="text-parchment/72 text-base sm:text-lg leading-[1.78] max-w-xl mb-8">
            {hasPersonas
              ? buildCopy(personasLeft)
              : `You have ${personasLimit} builds this week. Use one to bring your first person to life.`}
          </p>

          {/* Allowance card + CTA — stacks on mobile */}
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-6 lg:gap-10 items-start">
            <AllowanceCard allowance={allowance} loaded={loaded} />
            <div className="flex flex-col gap-3 lg:items-end">
              <Link
                href="/generate"
                className={
                  "block text-center font-mono text-[11px] font-medium tracking-widest uppercase px-7 py-3 transition-opacity " +
                  (personasLeft > 0
                    ? "bg-signal text-void hover:opacity-90"
                    : "bg-parchment/10 text-parchment/40 cursor-not-allowed pointer-events-none")
                }
              >
                {personasLeft > 0 ? "Build a new person →" : "Reset Monday"}
              </Link>
              {personasLeft === 0 && allowance?.resets_at && (
                <p className="text-[10px] font-mono text-parchment/40 tracking-widest uppercase text-center lg:text-right">
                  Allowance resets {formatResets(allowance.resets_at)}
                </p>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── 2. YOUR PERSONAS ──────────────────────────────────── */}
      {hasPersonas && (
        <section className="px-4 sm:px-6 lg:px-14 py-8 sm:py-12 border-t border-parchment/10">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-baseline justify-between gap-4 mb-6">
              <h2 className="font-condensed font-bold text-parchment uppercase tracking-wider text-xl sm:text-2xl">
                Your personas
              </h2>
              <span className="font-mono text-[10px] text-static tracking-widest uppercase">
                {personas.length} active
              </span>
            </div>

            {/* Mobile: horizontal scroll; lg+: grid */}
            <div className="flex gap-4 overflow-x-auto pb-2 lg:grid lg:grid-cols-4 lg:overflow-visible snap-x snap-mandatory" style={{ scrollbarWidth: "none" }}>
              {personas.map((p) => (
                <PersonaCard key={p.persona_id} p={p} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── 3. COMMUNITY WALL ─────────────────────────────────── */}
      <section className="border-t border-parchment/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-14 pt-8 sm:pt-12 pb-4">
          <div className="flex items-baseline justify-between gap-4 mb-6">
            <h2 className="font-condensed font-bold text-parchment uppercase tracking-wider text-xl sm:text-2xl">
              The wall
            </h2>
            <Link href="/community" className="font-mono text-[10px] text-parchment/60 hover:text-signal tracking-widest uppercase">
              See all →
            </Link>
          </div>
        </div>
        <div className="relative h-[40vh] sm:h-[50vh] overflow-hidden border-y border-parchment/5">
          <LivePersonaWall />
        </div>
      </section>
    </div>
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
      className="group flex-shrink-0 w-[260px] sm:w-[280px] lg:w-auto snap-start border border-parchment/10 hover:border-signal/40 transition-colors flex flex-col"
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
