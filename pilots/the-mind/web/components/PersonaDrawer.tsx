"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { PersonaCard, generateExemplarPortrait, fetchPersonaFull } from "@/lib/api";

interface Props {
  slug: string | null;
  initialCard: PersonaCard | null;
  onClose: () => void;
}

function TrustBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-static w-20 capitalize shrink-0">{label}</span>
      <div className="flex-1 h-px bg-parchment/10">
        <div className="h-px bg-signal" style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[10px] text-static w-8 text-right">{pct}%</span>
    </div>
  );
}

export default function PersonaDrawer({ slug, initialCard, onClose }: Props) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [full, setFull] = useState<Record<string, any> | null>(null);
  const [portraitUrl, setPortraitUrl] = useState<string | null>(initialCard?.portrait_url ?? null);
  const [portraitLoading, setPortraitLoading] = useState(false);
  const [portraitError, setPortraitError] = useState("");
  const drawerRef = useRef<HTMLDivElement>(null);

  const open = slug !== null;

  // Load full persona data when slug changes
  useEffect(() => {
    setFull(null);
    setPortraitUrl(initialCard?.portrait_url ?? null);
    setPortraitError("");
    if (!slug) return;
    fetchPersonaFull(slug).then(setFull).catch(() => {});
  }, [slug, initialCard]);

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") onClose(); }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Close on backdrop click
  function handleBackdropClick(e: React.MouseEvent) {
    if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) onClose();
  }

  async function handleGeneratePortrait() {
    if (!slug) return;
    setPortraitLoading(true);
    setPortraitError("");
    try {
      const url = await generateExemplarPortrait(slug);
      setPortraitUrl(url);
    } catch (e: unknown) {
      setPortraitError(e instanceof Error ? e.message : "Failed");
    } finally {
      setPortraitLoading(false);
    }
  }

  // Extract data safely
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const da = full ? (full.demographic_anchor as Record<string, any>) : null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const narrative = full ? (full.narrative as Record<string, any>) : null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const di = full ? (full.derived_insights as Record<string, any>) : null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const bt = full ? (full.behavioural_tendencies as Record<string, any>) : null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const memory = full ? ((full.memory as Record<string, any>)?.core as Record<string, any>) : null;
  const decisionBullets = full ? (full.decision_bullets as string[]) : null;
  const lifeStories = full ? (full.life_stories as Array<Record<string, unknown>>) : null;

  const trustOrientation = bt?.trust_orientation as Record<string, number> | undefined;

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-void/80 transition-opacity duration-200 ${open ? "opacity-100" : "opacity-0 pointer-events-none"}`}
        onClick={handleBackdropClick}
      />

      {/* Drawer */}
      <div
        ref={drawerRef}
        className={`fixed top-0 right-0 z-50 h-full w-full sm:max-w-xl bg-void border-l border-parchment/10
          overflow-y-auto transition-transform duration-300 ease-out
          ${open ? "translate-x-0" : "translate-x-full"}`}
      >
        {/* Close button */}
        <div className="sticky top-0 z-10 bg-void border-b border-parchment/10 px-6 py-4 flex items-center justify-between">
          <span className="text-[10px] font-mono text-static">
            {initialCard?.life_stage?.replace(/_/g, " ")} · {initialCard?.persona_id}
          </span>
          <button onClick={onClose} className="text-static hover:text-parchment transition-colors font-mono text-sm">✕</button>
        </div>

        <div className="px-4 py-6 md:px-6 md:py-8 space-y-8">
          {/* Portrait */}
          <div>
            {portraitUrl ? (
              <div className="relative w-full aspect-[4/3]">
                <Image
                  src={portraitUrl}
                  alt={initialCard?.name ?? ""}
                  fill
                  sizes="(min-width: 1024px) 480px, 100vw"
                  loading="lazy"
                  className="object-cover"
                />
              </div>
            ) : (
              <div className="w-full aspect-[4/3] bg-parchment/5 border border-parchment/10 flex flex-col items-center justify-center gap-4">
                <span className="font-condensed font-bold text-7xl text-parchment/10">
                  {initialCard?.name?.[0]}
                </span>
                <button
                  onClick={handleGeneratePortrait}
                  disabled={portraitLoading}
                  className="px-4 py-2 text-xs font-mono border border-parchment/20 text-static
                             hover:border-parchment/40 hover:text-parchment transition-colors
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {portraitLoading ? "Generating…" : "Generate portrait"}
                </button>
                {portraitError && (
                  <p className="text-[10px] font-mono text-static px-4 text-center">{portraitError}</p>
                )}
              </div>
            )}
          </div>

          {/* Name / hero */}
          <div>
            <h2 className="font-condensed font-bold text-parchment leading-none mb-1" style={{ fontSize: "clamp(32px,4vw,48px)" }}>
              {initialCard?.name}
            </h2>
            <p className="text-static text-sm">
              {initialCard?.age} · {initialCard?.city}, {initialCard?.country}
            </p>
            {initialCard?.description && (
              <p className="text-parchment/70 text-sm mt-3 leading-relaxed">{initialCard.description}</p>
            )}
          </div>

          {/* Narrative */}
          {narrative?.third_person && (
            <div className="border-t border-parchment/10 pt-6">
              <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-3">Profile</p>
              <p className="text-sm text-parchment/80 leading-relaxed">{narrative.third_person as string}</p>
            </div>
          )}

          {/* Identity */}
          {memory?.identity_statement && (
            <div className="border-t border-parchment/10 pt-6">
              <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-3">In their own words</p>
              <blockquote className="border-l-2 border-signal pl-4 text-sm text-parchment/75 italic leading-relaxed">
                {memory.identity_statement as string}
              </blockquote>
            </div>
          )}

          {/* Decision psychology */}
          {di && (
            <div className="border-t border-parchment/10 pt-6">
              <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-4">Decision psychology</p>
              <div className="grid grid-cols-2 gap-3">
                {[
                  ["Style", (di.decision_style as string)?.replace(/_/g, " ")],
                  ["Values", (di.primary_value_orientation as string)?.replace(/_/g, " ")],
                  ["Trust", (di.trust_anchor as string)?.replace(/_/g, " ")],
                  ["Risk", (di.risk_appetite as string)?.replace(/_/g, " ")],
                ].map(([label, value]) => value && (
                  <div key={label as string} className="border border-parchment/10 px-3 py-2">
                    <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-1">{label as string}</p>
                    <p className="text-xs text-parchment capitalize">{value as string}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Decision bullets */}
          {decisionBullets && decisionBullets.length > 0 && (
            <div className="border-t border-parchment/10 pt-6">
              <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-3">How they decide</p>
              <ul className="space-y-2">
                {decisionBullets.slice(0, 5).map((b, i) => (
                  <li key={i} className="flex gap-3 text-sm text-parchment/75">
                    <span className="text-signal font-mono text-xs mt-0.5 shrink-0">→</span>
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Trust orientation */}
          {trustOrientation && Object.keys(trustOrientation).length > 0 && (
            <div className="border-t border-parchment/10 pt-6">
              <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-4">Trust orientation</p>
              <div className="space-y-3">
                {Object.entries(trustOrientation).map(([k, v]) => (
                  <TrustBar key={k} label={k} value={v} />
                ))}
              </div>
            </div>
          )}

          {/* Life stories */}
          {lifeStories && lifeStories.length > 0 && (
            <div className="border-t border-parchment/10 pt-6">
              <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-4">Defining moments</p>
              <div className="space-y-4">
                {lifeStories.slice(0, 3).map((s, i) => (
                  <div key={i} className="border-l-2 border-parchment/10 pl-4">
                    <p className="text-xs font-semibold text-parchment/90 mb-1">{s.title as string}</p>
                    <p className="text-xs text-parchment/55 leading-relaxed line-clamp-3">{s.narrative as string}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* CTA */}
          <div className="border-t border-parchment/10 pt-6">
            <Link
              href={`/${slug}`}
              className="block w-full py-3 bg-signal text-void font-condensed font-bold text-base
                         tracking-wide text-center hover:bg-parchment transition-colors"
            >
              Ask {initialCard?.name?.split(" ")[0]} a question →
            </Link>
          </div>

          {!full && slug && (
            <p className="text-center font-mono text-[10px] text-static">Loading profile…</p>
          )}
        </div>
      </div>
    </>
  );
}
