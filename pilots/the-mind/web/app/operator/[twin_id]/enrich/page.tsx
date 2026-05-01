"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getTwin, enrichTwin, type TwinDetail } from "@/lib/operator-api";

// ── Icons ──────────────────────────────────────────────────────────────────

function chevronLeft() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── Signal hints ───────────────────────────────────────────────────────────

const SIGNAL_HINTS = [
  "A recent LinkedIn post or article they wrote",
  "Notes from a previous call or meeting",
  "Company press release or earnings commentary",
  "Podcast or conference transcript excerpt",
  "Email thread or reply they sent you",
  "Peer or colleague description of how they operate",
  "CRM notes from a past deal or interaction",
];

// ── Main page ──────────────────────────────────────────────────────────────

export default function EnrichPage() {
  const params = useParams<{ twin_id: string }>();
  const twinId = params.twin_id;
  const router = useRouter();

  const [twin, setTwin] = useState<TwinDetail | null>(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);

  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    getTwin(twinId)
      .then(setTwin)
      .catch(() => setPageError("Failed to load Twin."))
      .finally(() => setPageLoading(false));
  }, [twinId]);

  // Auto-resize
  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value);
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 480)}px`;
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || submitting) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      await enrichTwin(twinId, trimmed);
      setDone(true);
      // Brief pause so user sees the success state before redirect
      setTimeout(() => router.push(`/operator/${twinId}`), 1200);
    } catch (err) {
      setSubmitError((err as Error).message ?? "Enrichment failed.");
      setSubmitting(false);
    }
  }

  // ── Loading / error ────────────────────────────────────────────────────

  if (pageLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <span className="text-static text-xs font-mono animate-pulse">Loading…</span>
      </div>
    );
  }

  if (pageError || !twin) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-3">
          <p className="text-static text-sm">{pageError ?? "Twin not found."}</p>
          <Link href="/operator" className="text-parchment text-sm underline">
            ← Back to Twins
          </Link>
        </div>
      </div>
    );
  }

  const twinName = twin.full_name;
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="shrink-0 flex items-center gap-3 px-6 py-3 border-b border-white/8">
        <Link
          href={`/operator/${twinId}`}
          className="text-static hover:text-parchment transition-colors"
        >
          {chevronLeft()}
        </Link>
        <div>
          <span className="text-parchment text-sm font-semibold">{twinName}</span>
          <span className="text-static text-xs font-mono ml-2">/ Enrich</span>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8 space-y-8">

          {/* Intro */}
          <div className="space-y-2">
            <p className="text-static text-[10px] font-mono uppercase tracking-wider">
              Add new intelligence
            </p>
            <h1 className="text-parchment text-xl font-semibold leading-snug">
              Enrich {twinName}&#39;s Twin
            </h1>
            <p className="text-static text-sm leading-relaxed">
              Paste any text that reveals how {twinName} thinks, decides, or communicates.
              The Twin will be re-synthesised to incorporate the new signal — previous
              recon is preserved.
            </p>
          </div>

          {/* Signal hints */}
          <div className="border border-white/8 bg-white/2 px-4 py-4 space-y-2">
            <p className="text-static text-[10px] font-mono uppercase tracking-wider mb-3">
              What works well
            </p>
            <ul className="space-y-1.5">
              {SIGNAL_HINTS.map((hint) => (
                <li key={hint} className="flex items-start gap-2 text-sm text-static">
                  <span className="mt-1.5 w-1 h-1 rounded-full bg-static/40 shrink-0" />
                  {hint}
                </li>
              ))}
            </ul>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-static text-[10px] font-mono uppercase tracking-wider">
                  Signal text
                </label>
                <span className="text-static text-[10px] font-mono">
                  {wordCount > 0 ? `${wordCount} words` : ""}
                </span>
              </div>
              <textarea
                ref={textareaRef}
                value={text}
                onChange={handleChange}
                placeholder={`Paste text here — a LinkedIn post, call notes, article excerpt, or anything that reveals how ${twinName} operates…`}
                disabled={submitting || done}
                rows={10}
                className="w-full resize-none bg-white/4 border border-white/10 text-parchment text-sm placeholder:text-static/40 px-4 py-3 focus:outline-none focus:border-white/20 disabled:opacity-50 transition-colors leading-relaxed"
                style={{ minHeight: 200 }}
              />
              {submitError && (
                <p className="text-red-400 text-xs font-mono">{submitError}</p>
              )}
            </div>

            <div className="flex items-center justify-between pt-1">
              <p className="text-static text-[10px] font-mono max-w-xs leading-relaxed">
                Enrichment re-runs synthesis. The Twin profile will update
                within a few seconds.
              </p>

              {done ? (
                <div className="flex items-center gap-2 text-signal text-sm font-mono">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M2 7l4 4 6-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Enriched — redirecting…
                </div>
              ) : (
                <button
                  type="submit"
                  disabled={!text.trim() || submitting}
                  className="text-sm font-mono text-void bg-parchment px-5 py-2.5 hover:bg-parchment/80 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  {submitting ? (
                    <span className="animate-pulse">Enriching…</span>
                  ) : (
                    "Enrich Twin"
                  )}
                </button>
              )}
            </div>
          </form>

          {/* Current gaps callout */}
          {twin.gaps && twin.gaps.length > 0 && (
            <div className="border border-white/8 bg-white/2 px-4 py-4 space-y-2">
              <p className="text-static text-[10px] font-mono uppercase tracking-wider">
                Known gaps in this Twin
              </p>
              <ul className="space-y-1.5">
                {twin.gaps.map((gap, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-static">
                    <span className="mt-1.5 w-1 h-1 rounded-full bg-amber-400/50 shrink-0" />
                    {gap}
                  </li>
                ))}
              </ul>
              <p className="text-static text-[10px] font-mono pt-1">
                Enriching with targeted signal can close these gaps.
              </p>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
