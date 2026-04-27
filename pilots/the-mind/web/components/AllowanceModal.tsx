"use client";

/**
 * AllowanceModal.tsx — Hard-wall modal shown when a 402 allowance_exceeded
 * response is returned from the FastAPI backend.
 *
 * Shows:
 *   - Which action was exceeded
 *   - Full allowance summary (1 persona · 3 probes · 5 chats)
 *   - Reset countdown
 *   - Two CTAs: "Wait for reset" and "Book a call to scale up →"
 *
 * Consumed by AllowanceProvider — rendered globally.
 */
import { useEffect } from "react";

const CALENDLY = "https://calendly.com/iqbal-simulatte";

export interface AllowanceExceededPayload {
  action: "persona" | "probe" | "chat";
  used: number;
  limit: number;
  resets_at: string;
  upgrade_url: string;
}

interface Props {
  payload: AllowanceExceededPayload;
  onClose: () => void;
}

const ACTION_LABEL: Record<string, string> = {
  persona: "persona generation",
  probe: "Litmus probe",
  chat: "chat message",
};

function timeUntilDetailed(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "now";
  const d = Math.floor(ms / 86400000);
  const h = Math.floor((ms % 86400000) / 3600000);
  if (d > 0 && h > 0) return `${d} day${d > 1 ? "s" : ""} and ${h}h`;
  if (d > 0) return `${d} day${d > 1 ? "s" : ""}`;
  if (h > 0) return `${h} hour${h > 1 ? "s" : ""}`;
  return "less than an hour";
}

function resetLocalTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    weekday: "long",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZoneName: "short",
  });
}

export default function AllowanceModal({ payload, onClose }: Props) {
  // Close on Escape
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const actionLabel = ACTION_LABEL[payload.action] ?? payload.action;
  const resetIn = timeUntilDetailed(payload.resets_at);
  const resetLocal = resetLocalTime(payload.resets_at);

  return (
    <div
      className="fixed inset-0 bg-void/90 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-[#111] border border-parchment/15 rounded max-w-md w-full p-8 shadow-2xl">
        {/* Signal dot */}
        <div className="w-2 h-2 bg-amber-400/80 rounded-full mb-6" />

        <h2 className="text-parchment font-condensed font-black text-2xl tracking-wide mb-2 leading-tight">
          You&apos;ve used this week&apos;s {actionLabel}.
        </h2>

        <p className="text-parchment/55 text-sm leading-relaxed mb-6">
          The free tier resets every Monday so you can try The Mind without a credit card.
          Need more — or want to bring this to your team? Book a 20-min call.
        </p>

        {/* Allowance summary */}
        <ul className="space-y-1.5 mb-6">
          {[
            { label: "1 persona generated", key: "persona" },
            { label: "3 probes used", key: "probe" },
            { label: "5 chats sent", key: "chat" },
          ].map(item => (
            <li key={item.key} className="flex items-center gap-2 text-sm">
              <span className={`w-1.5 h-1.5 rounded-full ${item.key === payload.action ? "bg-amber-400" : "bg-parchment/20"}`} />
              <span className={item.key === payload.action ? "text-parchment font-medium" : "text-parchment/45"}>
                {item.label}
              </span>
            </li>
          ))}
        </ul>

        {/* Reset info */}
        <div className="bg-parchment/4 border border-parchment/10 rounded p-3 mb-6">
          <p className="text-parchment/60 text-xs font-mono leading-relaxed">
            Resets {resetLocal}
            <br />
            <span className="text-parchment/35">in {resetIn}</span>
          </p>
        </div>

        {/* CTAs */}
        <div className="flex flex-col gap-3">
          <a
            href={CALENDLY}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full text-center bg-signal hover:bg-signal/90 text-void font-bold text-sm py-3 rounded transition-colors"
          >
            Book a call to scale up →
          </a>
          <button
            onClick={onClose}
            className="w-full text-parchment/45 hover:text-parchment/70 text-sm py-2 transition-colors"
          >
            Wait for reset
          </button>
        </div>
      </div>
    </div>
  );
}
