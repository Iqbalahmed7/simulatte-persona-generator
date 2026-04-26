"use client";

import { useState } from "react";
import { PersonaCard } from "@/lib/api";
import PersonaDrawer from "./PersonaDrawer";

const STYLE_LABELS: Record<string, string> = {
  analytical: "Analytical", emotional: "Emotional",
  habitual: "Habitual", social: "Social",
};
const VALUE_LABELS: Record<string, string> = {
  price: "Price-first", quality: "Quality-first",
  brand: "Brand-driven", convenience: "Convenience",
  features: "Feature-focused",
};
const TRUST_LABELS: Record<string, string> = {
  self: "Self-reliant", peer: "Peer-driven",
  authority: "Authority", family: "Family",
};

function Badge({ label }: { label: string }) {
  return (
    <span className="inline-block px-2 py-0.5 text-[11px] font-mono font-medium border border-parchment/10 text-static">
      {label}
    </span>
  );
}

function ConsistencyBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2 mt-3">
      <div className="flex-1 h-px bg-parchment/10">
        <div className="h-px bg-signal" style={{ width: `${score}%` }} />
      </div>
      <span className="font-mono text-[10px] text-static">{score}</span>
    </div>
  );
}

function PersonaCardUI({ p, onClick }: { p: PersonaCard; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="group block w-full text-left border border-parchment/10 hover:border-parchment/25 transition-colors"
    >
      {/* Portrait */}
      {p.portrait_url ? (
        <img
          src={p.portrait_url}
          alt={p.name}
          className="w-full aspect-[4/3] object-cover"
        />
      ) : (
        <div className="w-full aspect-[4/3] bg-parchment/5 flex items-center justify-center border-b border-parchment/10">
          <span className="font-condensed font-bold text-5xl text-parchment/15">{p.name[0]}</span>
        </div>
      )}

      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-1">
              {p.life_stage.replace(/_/g, " ")}
            </p>
            <h2 className="font-condensed font-bold text-2xl text-parchment leading-none">
              {p.name}
            </h2>
            <p className="text-static text-sm mt-1">
              {p.age} · {p.city}, {p.country}
            </p>
          </div>
          <span className="font-mono text-[10px] text-static">{p.persona_id}</span>
        </div>

        <p className="text-sm text-parchment/75 leading-relaxed mb-4 line-clamp-2">
          {p.description}
        </p>

        <div className="flex flex-wrap gap-1.5 mb-3">
          <Badge label={STYLE_LABELS[p.decision_style] ?? p.decision_style} />
          <Badge label={VALUE_LABELS[p.primary_value_orientation] ?? p.primary_value_orientation} />
          <Badge label={TRUST_LABELS[p.trust_anchor] ?? p.trust_anchor} />
        </div>

        <ConsistencyBar score={p.consistency_score} />

        <p className="mt-4 text-[11px] font-semibold tracking-widest uppercase text-static group-hover:text-parchment/50 transition-colors">
          View profile →
        </p>
      </div>
    </button>
  );
}

export default function PersonaGrid({ personas }: { personas: PersonaCard[] }) {
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const activePersona = personas.find((p) => p.slug === activeSlug) ?? null;

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-parchment/10">
        {personas.map((p) => (
          <div key={p.slug} className="bg-void">
            <PersonaCardUI p={p} onClick={() => setActiveSlug(p.slug)} />
          </div>
        ))}
      </div>

      <PersonaDrawer
        slug={activeSlug}
        initialCard={activePersona}
        onClose={() => setActiveSlug(null)}
      />
    </>
  );
}
