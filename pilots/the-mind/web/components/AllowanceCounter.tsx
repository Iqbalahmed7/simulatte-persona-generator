"use client";

/**
 * AllowanceCounter.tsx — Small badge showing weekly usage.
 *
 * Display: "Personas 0/1 · Probes 0/3 · Chats 0/5 · Resets in 4d"
 *
 * Clicking opens a popover with detail + Calendly CTA.
 * Placed in the page header on /generate, /persona/*, /probe/* pages.
 */
import { useEffect, useRef, useState } from "react";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();
const CALENDLY = "https://calendly.com/iqbal-simulatte";

interface AllowanceState {
  personas: { used: number; limit: number };
  probes: { used: number; limit: number };
  chats: { used: number; limit: number };
  resets_at: string;
}

function timeUntil(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "now";
  const d = Math.floor(ms / 86400000);
  const h = Math.floor((ms % 86400000) / 3600000);
  if (d > 0) return `${d}d`;
  if (h > 0) return `${h}h`;
  return "< 1h";
}

function Bar({ used, limit }: { used: number; limit: number }) {
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  const full = used >= limit;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-parchment/10 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${full ? "bg-red-400/70" : "bg-signal"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-mono tabular-nums ${full ? "text-red-400/80" : "text-parchment/50"}`}>
        {used}/{limit}
      </span>
    </div>
  );
}

export default function AllowanceCounter() {
  const [allowance, setAllowance] = useState<AllowanceState | null>(null);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function load() {
      try {
        const tokRes = await fetch("/api/token", { cache: "no-store" });
        if (!tokRes.ok) return;
        const { token } = await tokRes.json();
        if (!token) return;
        const res = await fetch(`${API}/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const data = await res.json();
        setAllowance(data.allowance);
      } catch { /* silent */ }
    }
    load();
  }, []);

  // Close popover on outside click
  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  if (!allowance) return null;

  const resets = timeUntil(allowance.resets_at);

  const summary = [
    `Personas ${allowance.personas.used}/${allowance.personas.limit}`,
    `Probes ${allowance.probes.used}/${allowance.probes.limit}`,
    `Chats ${allowance.chats.used}/${allowance.chats.limit}`,
    `Resets in ${resets}`,
  ].join(" · ");

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="text-parchment/40 hover:text-parchment/70 text-xs font-mono transition-colors leading-none"
        aria-label="View allowance details"
      >
        {summary}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-64 bg-void border border-parchment/15 rounded shadow-2xl z-50 p-4 space-y-4">
          <p className="text-parchment font-condensed font-bold text-sm tracking-wide">
            Weekly allowance
          </p>

          <div className="space-y-3">
            <div>
              <p className="text-parchment/50 text-xs mb-1">Persona generations</p>
              <Bar used={allowance.personas.used} limit={allowance.personas.limit} />
            </div>
            <div>
              <p className="text-parchment/50 text-xs mb-1">Litmus probes</p>
              <Bar used={allowance.probes.used} limit={allowance.probes.limit} />
            </div>
            <div>
              <p className="text-parchment/50 text-xs mb-1">Chat messages</p>
              <Bar used={allowance.chats.used} limit={allowance.chats.limit} />
            </div>
          </div>

          <div className="border-t border-parchment/10 pt-3">
            <p className="text-parchment/35 text-xs font-mono mb-3">
              Resets Monday 00:00 UTC · in {resets}
            </p>
            <a
              href={CALENDLY}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full text-center bg-signal/10 hover:bg-signal/20 border border-signal/30 text-signal text-xs font-mono py-2 rounded transition-colors"
            >
              Book a call to scale up →
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
