/**
 * WallTicker — slow-moving vertical feed of community personas for
 * the right rail of the dashboard.
 *
 * Renders compact cards (portrait + name + city) auto-scrolling top
 * to bottom, ~75s per cycle, pause on hover. The list is duplicated
 * once so the loop appears seamless. CSS-only — no rAF, no JS scroll
 * math.
 *
 * Hidden below lg — the dashboard center column expands to fill in
 * its place.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { API } from "@/lib/api";

interface CommunityPersona {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  country: string;
  portrait_url: string | null;
}

export default function WallTicker() {
  const [items, setItems] = useState<CommunityPersona[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/community/personas?limit=30`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : []))
      .then((list) => {
        if (cancelled) return;
        const filtered = (Array.isArray(list) ? list : []).filter(
          (p: CommunityPersona) => p.portrait_url && p.name,
        );
        setItems(filtered);
      })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, []);

  if (items.length === 0) {
    return (
      <aside className="hidden lg:flex flex-col border-l border-parchment/10 bg-void sticky top-0 self-start h-screen flex-shrink-0 w-[320px]">
        <div className="px-5 pt-5 pb-3 border-b border-parchment/5">
          <p className="text-[10px] font-mono text-static uppercase tracking-[0.18em]">
            The wall · Live
          </p>
        </div>
        <div className="flex-1 flex items-center justify-center px-5">
          <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em]">
            Loading…
          </p>
        </div>
      </aside>
    );
  }

  // Duplicate for seamless loop
  const loop = [...items, ...items];

  return (
    <aside className="hidden lg:flex flex-col border-l border-parchment/10 bg-void sticky top-0 self-start h-screen flex-shrink-0 w-[320px] overflow-hidden">
      <div className="px-5 pt-5 pb-3 border-b border-parchment/5 flex items-center justify-between flex-shrink-0">
        <p className="text-[10px] font-mono text-static uppercase tracking-[0.18em]">
          The wall · Live
        </p>
        <Link href="/community" className="text-[10px] font-mono text-static hover:text-signal uppercase tracking-[0.18em]">
          See all →
        </Link>
      </div>

      {/* Ticker viewport */}
      <div className="flex-1 relative overflow-hidden ticker-viewport">
        <div className="ticker-track flex flex-col gap-3 px-3 py-3">
          {loop.map((p, i) => (
            <TickerCard key={`${p.persona_id}-${i}`} p={p} />
          ))}
        </div>
        {/* Top + bottom fade so cards don't pop in/out abruptly */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-10 bg-gradient-to-b from-void to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-void to-transparent" />
      </div>

      <style>{`
        .ticker-viewport:hover .ticker-track { animation-play-state: paused; }
        .ticker-track {
          animation: ticker-scroll 75s linear infinite;
          will-change: transform;
        }
        @keyframes ticker-scroll {
          0%   { transform: translateY(0); }
          100% { transform: translateY(-50%); }
        }
        @media (prefers-reduced-motion: reduce) {
          .ticker-track { animation: none; }
        }
      `}</style>
    </aside>
  );
}

function TickerCard({ p }: { p: CommunityPersona }) {
  const place = [p.city, p.country].filter(Boolean).join(", ");
  return (
    <Link
      href={`/persona/${p.persona_id}`}
      className="group flex items-center gap-3 border border-parchment/10 hover:border-signal/40 transition-colors p-2"
    >
      <div className="w-12 h-12 flex-shrink-0 overflow-hidden">
        {p.portrait_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={p.portrait_url}
            alt=""
            loading="lazy"
            className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
          />
        ) : (
          <div className="w-full h-full bg-parchment/[0.05]" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-condensed font-bold text-parchment text-sm leading-tight truncate">
          {p.name}
          {p.age ? <span className="text-parchment/60 font-normal">, {p.age}</span> : null}
        </div>
        {place && (
          <div className="font-mono text-[9px] text-static tracking-widest uppercase truncate mt-0.5">
            {place}
          </div>
        )}
      </div>
    </Link>
  );
}
