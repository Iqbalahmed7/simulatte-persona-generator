/**
 * PersonaPicker — modal that lets a user pick an existing persona
 * (to chat with or run a probe against), or generate a new one.
 *
 * Triggered from the dashboard sidebar's "Ask a question" / "Run a probe"
 * actions. Click an existing persona portrait → routes to that persona's
 * chat or probe page. Click "Build new" → /generate (their generation will
 * be available next; we don't yet auto-route to the chosen action after
 * generation, but that's a small future enhancement).
 *
 * Mobile-friendly: portrait grid wraps; close on backdrop tap or Esc.
 */
"use client";

import { useEffect } from "react";
import Link from "next/link";

export type PickerMode = "chat" | "probe";

interface MyPersona {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  portrait_url: string | null;
}

export default function PersonaPicker({
  mode,
  personas,
  onClose,
}: {
  mode: PickerMode;
  personas: MyPersona[];
  onClose: () => void;
}) {
  // Esc to close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const titleVerb = mode === "chat" ? "ask" : "probe";
  const heading = mode === "chat" ? "Ask a question" : "Run a product probe";
  const sub =
    mode === "chat"
      ? "Pick a persona to chat with, or build a new one tailored to your question."
      : "Pick a persona to test your product against, or build a new one tailored to the brief.";
  const linkSuffix = mode === "probe" ? "/probe" : "";
  const generateHref = `/generate?next=${mode === "probe" ? "probe" : "chat"}`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={heading}
    >
      {/* Backdrop */}
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 bg-void/85 backdrop-blur-sm"
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-void border border-parchment/15 max-h-[85vh] overflow-y-auto">
        <div className="flex items-start justify-between p-5 sm:p-6 border-b border-parchment/10">
          <div className="min-w-0">
            <p className="text-[11px] font-mono text-signal uppercase tracking-[0.18em] mb-1">
              {mode.toUpperCase()}
            </p>
            <h2 className="font-condensed font-bold text-parchment text-2xl sm:text-3xl leading-tight">
              {heading}
            </h2>
            <p className="text-parchment/60 text-sm mt-2 max-w-md">{sub}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex-shrink-0 text-parchment/50 hover:text-parchment p-1 -m-1"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Existing personas */}
        {personas.length > 0 && (
          <div className="p-5 sm:p-6">
            <p className="text-[10px] font-mono text-static tracking-widest uppercase mb-3">
              {personas.length} persona{personas.length === 1 ? "" : "s"} you can {titleVerb}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {personas.map((p) => (
                <Link
                  key={p.persona_id}
                  href={`/persona/${p.persona_id}${linkSuffix}`}
                  className="group block border border-parchment/10 hover:border-signal/50 transition-colors"
                >
                  <div className="relative" style={{ aspectRatio: "3 / 4" }}>
                    {p.portrait_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={p.portrait_url}
                        alt=""
                        loading="lazy"
                        className="absolute inset-0 w-full h-full object-cover opacity-85 group-hover:opacity-100 transition-opacity"
                      />
                    ) : (
                      <div className="absolute inset-0 bg-parchment/[0.04] flex items-center justify-center">
                        <span className="font-mono text-[9px] text-static tracking-widest uppercase">
                          No portrait
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="p-2 border-t border-parchment/10">
                    <div className="font-condensed font-bold text-parchment text-sm truncate">
                      {p.name || "—"}
                      {p.age ? <span className="text-parchment/60 font-normal">, {p.age}</span> : null}
                    </div>
                    <div className="font-mono text-[9px] text-static tracking-widest uppercase truncate">
                      {[p.city, p.country].filter(Boolean).join(", ") || "—"}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Generate-new path */}
        <div className={
          "p-5 sm:p-6 " + (personas.length > 0 ? "border-t border-parchment/10" : "")
        }>
          <p className="text-[10px] font-mono text-static tracking-widest uppercase mb-3">
            Or build someone new
          </p>
          <Link
            href={generateHref}
            className="inline-block bg-signal text-void font-condensed font-bold uppercase tracking-wider px-6 py-3 hover:opacity-90 transition-opacity"
            onClick={onClose}
          >
            Build a new persona →
          </Link>
          <p className="text-parchment/50 text-xs mt-3">
            Tailor the brief to whoever you want to {titleVerb}. Counts against your
            weekly persona allowance.
          </p>
        </div>
      </div>
    </div>
  );
}
