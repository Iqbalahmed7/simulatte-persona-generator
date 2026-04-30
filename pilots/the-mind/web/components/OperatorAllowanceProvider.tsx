"use client";

/**
 * OperatorAllowanceProvider.tsx — Context + 402 modal for Operator actions.
 *
 * Parallel to AllowanceProvider.tsx but scoped to twin builds and probe
 * messages so counters don't collide with persona/probe/chat allowances.
 *
 * Usage:
 *   const { triggerOperatorAllowanceExceeded } = useOperatorAllowance();
 *
 *   // Or throw OperatorAllowanceError from an API call — the provider
 *   // wraps children and shows the modal automatically if you call trigger.
 */
import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import { type OperatorAllowanceError } from "@/lib/operator-api";

// ── Types ─────────────────────────────────────────────────────────────────

export interface OperatorAllowancePayload {
  action: string;
  used: number;
  limit: number;
  resets_at: string;
  upgrade_url?: string;
}

interface OperatorAllowanceContextValue {
  triggerOperatorAllowanceExceeded: (payload: OperatorAllowancePayload) => void;
}

// ── Context ───────────────────────────────────────────────────────────────

const OperatorAllowanceContext = createContext<OperatorAllowanceContextValue>({
  triggerOperatorAllowanceExceeded: () => undefined,
});

export function useOperatorAllowance() {
  return useContext(OperatorAllowanceContext);
}

// ── Provider ──────────────────────────────────────────────────────────────

export default function OperatorAllowanceProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [payload, setPayload] = useState<OperatorAllowancePayload | null>(null);

  const triggerOperatorAllowanceExceeded = useCallback(
    (p: OperatorAllowancePayload) => setPayload(p),
    []
  );

  return (
    <OperatorAllowanceContext.Provider value={{ triggerOperatorAllowanceExceeded }}>
      {children}
      {payload && (
        <OperatorAllowanceModal
          payload={payload}
          onClose={() => setPayload(null)}
        />
      )}
    </OperatorAllowanceContext.Provider>
  );
}

// ── Helper — call in catch blocks ─────────────────────────────────────────

/**
 * If err is an OperatorAllowanceError, trigger the modal and return true.
 * Otherwise return false so callers can re-throw or handle normally.
 */
export function handleOperatorAllowanceError(
  err: unknown,
  trigger: (p: OperatorAllowancePayload) => void
): boolean {
  if (
    err instanceof Error &&
    err.name === "OperatorAllowanceError" &&
    "payload" in err
  ) {
    trigger((err as OperatorAllowanceError).payload as OperatorAllowancePayload);
    return true;
  }
  return false;
}

// ── Modal ─────────────────────────────────────────────────────────────────

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

function actionLabel(action: string): string {
  const map: Record<string, string> = {
    twin_build: "Twin builds",
    probe_message: "Probe messages",
  };
  return map[action] ?? action;
}

function OperatorAllowanceModal({
  payload,
  onClose,
}: {
  payload: OperatorAllowancePayload;
  onClose: () => void;
}) {
  const resets = timeUntil(payload.resets_at);
  const label = actionLabel(payload.action);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-void border border-parchment/15 w-full max-w-sm mx-4 p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="space-y-1">
          <p className="text-[10px] font-mono text-signal uppercase tracking-[0.18em]">
            Operator · Weekly limit
          </p>
          <h2 className="font-condensed font-black text-parchment text-xl uppercase">
            {label} limit reached
          </h2>
        </div>

        {/* Usage */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs font-mono text-parchment/50">
            <span>{label}</span>
            <span>
              {payload.used} / {payload.limit}
            </span>
          </div>
          <div className="h-1 bg-parchment/10 overflow-hidden">
            <div className="h-full bg-parchment/30" style={{ width: "100%" }} />
          </div>
          <p className="text-parchment/35 text-xs font-mono">
            Resets Monday 00:00 UTC · in {resets}
          </p>
        </div>

        {/* CTA */}
        <div className="space-y-2 pt-1">
          <a
            href={payload.upgrade_url ?? CALENDLY}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full text-center bg-signal/10 hover:bg-signal/20 border border-signal/30 text-signal text-xs font-mono py-2.5 transition-colors"
          >
            Book a call to scale up →
          </a>
          <button
            onClick={onClose}
            className="block w-full text-center text-parchment/30 hover:text-parchment/60 text-xs font-mono py-2 transition-colors"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
