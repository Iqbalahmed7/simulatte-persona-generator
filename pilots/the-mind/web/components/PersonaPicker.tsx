/**
 * PersonaPicker — modal that lets a user pick who to ask / probe.
 *
 * Three paths in order of preference:
 *   1. One of YOUR personas (if you have any)
 *   2. A COMMUNITY persona from the wall (no allowance cost)
 *   3. BUILD A NEW persona (counts against weekly allowance)
 *
 * For users with zero own personas (every brand-new invitee), paths 2
 * and 3 keep the modal useful instead of dead-ending with just a
 * "Build new" CTA.
 *
 * Mobile-friendly: portrait grid wraps; close on backdrop tap or Esc.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { API } from "@/lib/api";

export type PickerMode = "chat" | "probe";

interface MyPersona {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  portrait_url: string | null;
  occupation?: string;
  snippet?: string;
}

interface CommunityPersona {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  portrait_url: string | null;
  snippet?: string;
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
  const [community, setCommunity] = useState<CommunityPersona[]>([]);
  const [communityLoading, setCommunityLoading] = useState(true);
  const [showAllCommunity, setShowAllCommunity] = useState(false);

  // Esc to close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Fetch community personas — no auth needed, the endpoint is public.
  useEffect(() => {
    let cancelled = false;
    // Same-origin proxy with 60s cache — see app/api/community/personas/route.ts
    fetch(`/api/community/personas?limit=24`)
      .then((r) => (r.ok ? r.json() : []))
      .then((list) => {
        if (cancelled) return;
        const filtered = (Array.isArray(list) ? list : []).filter(
          (p: CommunityPersona) => p.portrait_url && p.name,
        );
        setCommunity(filtered);
        setCommunityLoading(false);
      })
      .catch(() => {
        if (!cancelled) setCommunityLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const titleVerb = mode === "chat" ? "ask" : "probe";
  const heading = mode === "chat" ? "Ask a question" : "Run a product probe";
  const sub =
    mode === "chat"
      ? "Pick someone to chat with — your personas, the community wall, or a fresh build."
      : "Pick someone to probe — your personas, the community wall, or a fresh build.";
  const linkSuffix = mode === "probe" ? "/probe" : "";
  const generateHref = `/generate?next=${mode === "probe" ? "probe" : "chat"}`;

  const ownIds = new Set(personas.map((p) => p.persona_id));
  const communityVisible = community.filter((c) => !ownIds.has(c.persona_id));
  const communityCapped = showAllCommunity ? communityVisible : communityVisible.slice(0, 6);

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
      <div
        className="relative w-full max-w-2xl bg-void border border-parchment/15 overflow-y-auto"
        style={{ maxHeight: "min(85vh, calc(100vh - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px) - 32px))" }}
      >
        <div className="flex items-start justify-between p-5 sm:p-6 border-b border-parchment/10 sticky top-0 bg-void z-10">
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

        {/* 1. YOUR personas — only when there's at least one */}
        {personas.length > 0 && (
          <div className="p-5 sm:p-6">
            <p className="text-[10px] font-mono text-signal tracking-widest uppercase mb-3">
              Your personas · {personas.length}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {personas.map((p) => (
                <PersonaTile key={p.persona_id} p={p} linkSuffix={linkSuffix} />
              ))}
            </div>
          </div>
        )}

        {/* 2. COMMUNITY personas — loading skeleton or list */}
        {communityLoading && communityVisible.length === 0 && (
          <div className={
            "p-5 sm:p-6 " + (personas.length > 0 ? "border-t border-parchment/10" : "")
          }>
            <p className="text-[10px] font-mono text-static tracking-widest uppercase mb-3">
              From the community wall · Loading…
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="border border-parchment/10 animate-pulse">
                  <div style={{ aspectRatio: "3 / 4" }} className="bg-parchment/[0.04]" />
                  <div className="p-3 space-y-2">
                    <div className="h-3 bg-parchment/[0.06] w-3/4" />
                    <div className="h-2 bg-parchment/[0.04] w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {communityVisible.length > 0 && (
          <div className={
            "p-5 sm:p-6 " + (personas.length > 0 ? "border-t border-parchment/10" : "")
          }>
            <div className="flex items-baseline justify-between gap-3 mb-3">
              <p className="text-[10px] font-mono text-static tracking-widest uppercase">
                From the community wall · {communityVisible.length}
              </p>
              {communityVisible.length > 6 && (
                <button
                  type="button"
                  onClick={() => setShowAllCommunity((v) => !v)}
                  className="text-[10px] font-mono text-static hover:text-signal tracking-widest uppercase"
                >
                  {showAllCommunity ? "Show less" : `Show all ${communityVisible.length}`}
                </button>
              )}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {communityCapped.map((p) => (
                <PersonaTile key={p.persona_id} p={p} linkSuffix={linkSuffix} />
              ))}
            </div>
            <p className="text-parchment/50 text-xs mt-4">
              Community personas are free to {titleVerb} — they don&#x2019;t count against
              your weekly persona allowance.
            </p>
          </div>
        )}

        {/* 3. Build new */}
        <div className={
          "p-5 sm:p-6 " +
          (personas.length > 0 || communityVisible.length > 0
            ? "border-t border-parchment/10"
            : "")
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

function PersonaTile({ p, linkSuffix }: { p: MyPersona; linkSuffix: string }) {
  const place = [p.city, p.country].filter(Boolean).join(", ");
  // Qualifier line — occupation if we have it, otherwise snippet, otherwise location.
  const qualifier = p.occupation || p.snippet || place;
  return (
    <Link
      href={`/persona/${p.persona_id}${linkSuffix}`}
      className="group block border border-parchment/10 hover:border-signal/50 transition-colors flex flex-col"
    >
      <div className="relative" style={{ aspectRatio: "3 / 4" }}>
        {p.portrait_url ? (
          <Image
            src={p.portrait_url}
            alt=""
            fill
            sizes="(min-width: 640px) 200px, 50vw"
            loading="lazy"
            className="object-cover opacity-85 group-hover:opacity-100 transition-opacity"
          />
        ) : (
          <div className="absolute inset-0 bg-parchment/[0.04] flex items-center justify-center">
            <span className="font-mono text-[9px] text-static tracking-widest uppercase">
              No portrait
            </span>
          </div>
        )}
      </div>
      <div className="p-3 border-t border-parchment/10 flex-1 flex flex-col">
        <div className="font-condensed font-bold text-parchment text-sm leading-tight truncate">
          {p.name || "—"}
          {p.age ? <span className="text-parchment/60 font-normal">, {p.age}</span> : null}
        </div>
        {place && (
          <div className="font-mono text-[9px] text-static tracking-widest uppercase truncate mt-1">
            {place}
          </div>
        )}
        {qualifier && qualifier !== place && (
          <div
            className="text-parchment/72 text-[11px] leading-snug mt-2 overflow-hidden"
            style={{
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
            }}
          >
            {qualifier}
          </div>
        )}
      </div>
    </Link>
  );
}
