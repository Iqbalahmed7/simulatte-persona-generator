/**
 * FeedbackModal — lightweight NPS-style prompt.
 *
 * Mount once at the app root (or per-surface). Auto-shows once per user
 * per surface, after they've taken N billable actions. localStorage
 * tracks "shown:<surface>" so it doesn't nag.
 *
 * Score 1-10 + optional one-line comment → POST /feedback.
 */
"use client";

import { useEffect, useState } from "react";
import { API } from "@/lib/api";

type Surface = "probe" | "chat" | "generate" | "general";

interface Props {
  /** Which surface triggered the prompt — sent to backend for tagging. */
  surface: Surface;
  /** Show the modal immediately, bypassing the localStorage gate. */
  force?: boolean;
}

const KEY = (s: Surface) => `mind:feedback:shown:${s}`;

export default function FeedbackModal({ surface, force = false }: Props) {
  const [open, setOpen] = useState(false);
  const [score, setScore] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (force) { setOpen(true); return; }
    if (typeof window === "undefined") return;
    if (localStorage.getItem(KEY(surface))) return;
    // Small delay so the modal doesn't fight a navigation
    const id = setTimeout(() => setOpen(true), 1200);
    return () => clearTimeout(id);
  }, [surface, force]);

  function close() {
    setOpen(false);
    if (typeof window !== "undefined") localStorage.setItem(KEY(surface), String(Date.now()));
  }

  async function submit() {
    if (score == null) return;
    setSubmitting(true);
    try {
      const t = await fetch("/api/token", { cache: "no-store" });
      const { token } = await t.json();
      await fetch(`${API}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ score, comment: comment.trim() || null, surface }),
      });
      setDone(true);
      setTimeout(close, 1200);
    } catch {
      close(); // fail silently — don't block the user
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-void/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-void border border-parchment/15 p-6">
        {done ? (
          <p className="text-parchment text-center py-4">
            Thanks — that helps a lot.
          </p>
        ) : (
          <>
            <div className="flex items-start justify-between mb-3">
              <p className="text-[10px] font-mono text-signal uppercase tracking-[0.18em]">
                Quick check
              </p>
              <button
                onClick={close}
                aria-label="Dismiss"
                className="text-parchment/40 hover:text-parchment text-lg leading-none"
              >
                ×
              </button>
            </div>
            <h2 className="font-condensed font-bold text-parchment text-2xl mb-1">
              How likely are you to recommend Simulatte to a colleague?
            </h2>
            <p className="text-parchment/60 text-sm mb-4">
              0 = not at all · 10 = certainly
            </p>
            <div className="grid grid-cols-11 gap-1 mb-4">
              {Array.from({ length: 11 }, (_, i) => (
                <button
                  key={i}
                  onClick={() => setScore(i)}
                  className={
                    "py-2 text-sm font-mono border transition-colors " +
                    (score === i
                      ? "bg-signal text-void border-signal"
                      : "border-parchment/15 text-parchment/70 hover:border-signal/60 hover:text-signal")
                  }
                >
                  {i}
                </button>
              ))}
            </div>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="One thing we could do better? (optional)"
              maxLength={500}
              rows={2}
              className="w-full bg-transparent border border-parchment/15 px-3 py-2 text-parchment placeholder-parchment/30 text-sm focus:outline-none focus:border-signal/60 mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={close}
                className="text-[11px] font-mono uppercase tracking-widest text-parchment/60 hover:text-parchment px-3 py-2"
              >
                Skip
              </button>
              <button
                onClick={submit}
                disabled={score == null || submitting}
                className="text-[11px] font-mono uppercase tracking-widest bg-signal text-void px-4 py-2 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {submitting ? "…" : "Send"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
