"use client";

/**
 * OperatorAllowanceCounter.tsx — Compact inline badge for the NavRail.
 *
 * Shows: "Twins 0/5" — tapping opens the same detail popover style as
 * AllowanceCounter.tsx but scoped to Operator actions only.
 *
 * Sits below the "Twins" nav label in expanded NavRail state.
 */
import { useEffect, useRef, useState } from "react";
import { getOperatorAllowance, type OperatorAllowanceState } from "@/lib/operator-api";

const CALENDLY = "https://calendly.com/iqbal-simulatte";

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
      <div className="flex-1 h-1 bg-parchment/10 overflow-hidden">
        <div
          className={`h-full transition-all ${full ? "bg-parchment/30" : "bg-signal"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={`text-xs font-mono tabular-nums ${
          full ? "text-parchment/30" : "text-parchment/50"
        }`}
      >
        {used}/{limit}
      </span>
    </div>
  );
}

export default function OperatorAllowanceCounter() {
  const [allowance, setAllowance] = useState<OperatorAllowanceState | null>(null);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getOperatorAllowance().then((a) => {
      if (a) setAllowance(a);
    });
  }, []);

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
  const twinsLeft = allowance.twins.limit - allowance.twins.used;
  const summary =
    twinsLeft > 0
      ? `${twinsLeft} build${twinsLeft === 1 ? "" : "s"} left this week`
      : "Resets Monday";

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="text-static hover:text-parchment/60 text-[10px] font-mono uppercase tracking-widest transition-colors leading-none truncate max-w-full"
        aria-label="Operator allowance details"
        title={summary}
      >
        {summary}
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-2 w-64 bg-void border border-parchment/15 z-50 p-4 space-y-4 shadow-2xl">
          <p className="text-parchment font-condensed font-bold text-sm tracking-wide uppercase">
            Operator allowance
          </p>

          <div className="space-y-3">
            <div>
              <p className="text-parchment/50 text-xs mb-1">Twin builds</p>
              <Bar
                used={allowance.twins.used}
                limit={allowance.twins.limit}
              />
            </div>
            <div>
              <p className="text-parchment/50 text-xs mb-1">Probe messages</p>
              <Bar
                used={allowance.probe_messages.used}
                limit={allowance.probe_messages.limit}
              />
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
              className="block w-full text-center bg-signal/10 hover:bg-signal/20 border border-signal/30 text-signal text-xs font-mono py-2 transition-colors"
            >
              Book a call to scale up →
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
