"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchGeneratedPersona, generatePortrait, GeneratedPersona } from "@/lib/api";
import GenuinenessChip from "@/components/GenuinenessChip";

// ── helpers ───────────────────────────────────────────────────────────────

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-parchment/10 pt-8 mt-8">
      <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-6">
        {label}
      </p>
      {children}
    </section>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-parchment/10 px-4 py-3">
      <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-1">{label}</p>
      <p className="text-sm text-parchment font-medium capitalize">{value.replace(/_/g, " ")}</p>
    </div>
  );
}

function TrustBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-static w-20 capitalize shrink-0">{label}</span>
      <div className="flex-1 h-px bg-parchment/10">
        <div className="h-px bg-signal transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[10px] text-static w-8 text-right">{pct}%</span>
    </div>
  );
}

// ── portrait component ────────────────────────────────────────────────────

function PortraitPanel({
  personaId,
  name,
  initialUrl,
}: {
  personaId: string;
  name: string;
  initialUrl?: string | null;
}) {
  const [url, setUrl] = useState<string | null>(initialUrl ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Auto-generate on mount if no portrait yet
  useEffect(() => {
    if (url) return;
    setLoading(true);
    generatePortrait(personaId)
      .then(setUrl)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Portrait generation failed"))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personaId]);

  if (url) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt={`Portrait of ${name}`}
        className="w-full aspect-[4/3] md:aspect-[3/4] object-cover border border-parchment/10"
      />
    );
  }

  return (
    <div className="w-full aspect-[3/4] border border-parchment/10 flex flex-col items-center justify-center gap-4 bg-parchment/[0.02]">
      {loading ? (
        <>
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 bg-signal"
                style={{ animation: `dot-pulse 1.2s ${i * 0.2}s ease-in-out infinite` }}
              />
            ))}
          </div>
          <p className="font-mono text-[10px] text-static">Rendering portrait…</p>
        </>
      ) : error ? (
        <p className="font-mono text-[10px] text-static text-center px-4">{error}</p>
      ) : null}
      <style>{`
        @keyframes dot-pulse {
          0%, 100% { opacity: 0.2; transform: scaleY(1); }
          50% { opacity: 1; transform: scaleY(1.6); }
        }
      `}</style>
    </div>
  );
}

// ── attribute accordion ───────────────────────────────────────────────────

function AttributeCategory({
  category,
  attrs,
}: {
  category: string;
  attrs: Record<string, { value: unknown; label: string; type: string; source: string }>;
}) {
  const [open, setOpen] = useState(false);
  const entries = Object.entries(attrs);

  return (
    <div className="border-b border-parchment/10 last:border-0">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between py-4 text-left"
      >
        <span className="text-sm text-parchment/75 capitalize font-medium">
          {category.replace(/_/g, " ")}
        </span>
        <span className="font-mono text-[10px] text-static">
          {entries.length} attrs {open ? "▲" : "▼"}
        </span>
      </button>
      {open && (
        <div className="pb-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {entries.map(([key, attr]) => (
            <div key={key} className="bg-parchment/[0.03] px-3 py-2.5">
              <p className="text-[10px] font-mono text-static uppercase tracking-wide mb-1">{key}</p>
              <p className="text-xs text-parchment/80">{String(attr.value)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── main page ─────────────────────────────────────────────────────────────

export default function PersonaProfilePage() {
  const { id } = useParams<{ id: string }>();
  const [persona, setPersona] = useState<GeneratedPersona | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchGeneratedPersona(id)
      .then(setPersona)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load persona"));
  }, [id]);

  if (error) {
    return (
      <main className="min-h-screen px-6 py-12 max-w-4xl mx-auto">
        <Link href="/" className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors">
          ← Home
        </Link>
        <div className="mt-12 border border-parchment/10 p-6">
          <p className="font-mono text-sm text-static">{error}</p>
          <p className="font-mono text-xs text-static/60 mt-2">
            Generated personas live in server memory — they reset on server restart.
          </p>
        </div>
      </main>
    );
  }

  if (!persona) {
    return (
      <main className="min-h-screen px-6 py-12 flex items-center justify-center">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-2 h-2 bg-signal"
              style={{ animation: `dot-pulse 1.2s ${i * 0.2}s ease-in-out infinite` }} />
          ))}
        </div>
        <style>{`@keyframes dot-pulse { 0%,100%{opacity:.2} 50%{opacity:1} }`}</style>
      </main>
    );
  }

  const { demographic_anchor: da, derived_insights: di, behavioural_tendencies: bt } = persona;

  return (
    <main className="min-h-screen px-4 py-6 md:px-6 md:py-12 max-w-5xl mx-auto">
      {/* Nav */}
      <div className="flex items-center justify-between mb-10">
        <Link href="/" className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors">
          ← Home
        </Link>
      </div>

      {/* Hero — portrait + identity */}
      <div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-8 mb-2">
        {/* Portrait */}
        <div className="shrink-0">
          <PortraitPanel personaId={persona.persona_id} name={da.name} initialUrl={persona.portrait_url} />
        </div>

        {/* Identity */}
        <div className="flex flex-col justify-between">
          <div>
            <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-2">
              {da.life_stage.replace(/_/g, " ")}
            </p>
            <h1 className="font-condensed font-bold text-parchment leading-none mb-1"
              style={{ fontSize: "clamp(36px,5vw,64px)" }}>
              {da.name}
            </h1>
            <p className="text-static text-base mb-5">
              {da.age} · {da.location.city}, {da.location.country}
            </p>

            {/* Genuineness + chat CTA */}
            <div className="flex flex-wrap items-center gap-3 mb-5">
              {persona.quality_assessment && (
                <GenuinenessChip assessment={persona.quality_assessment} />
              )}
              <Link
                href={`/persona/${persona.persona_id}/chat`}
                className="inline-flex items-center gap-2 bg-signal text-void font-condensed font-bold px-4 py-2 hover:bg-signal/90 transition-colors"
              >
                <span className="text-[11px] tracking-widest uppercase">
                  Talk to {persona.narrative.display_name || da.name.split(" ")[0]}
                </span>
                <span aria-hidden>→</span>
              </Link>
              <Link
                href={`/persona/${persona.persona_id}/probe`}
                className="inline-flex items-center gap-2 border border-signal text-signal font-condensed font-bold px-4 py-2 hover:bg-signal/10 transition-colors"
              >
                <span className="text-[11px] tracking-widest uppercase">
                  Test a product with {persona.narrative.display_name || da.name.split(" ")[0]}
                </span>
                <span aria-hidden>→</span>
              </Link>
            </div>

            <p className="text-parchment/80 text-sm leading-relaxed mb-6">
              {persona.narrative.third_person}
            </p>

            {/* Quick stats */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <StatPill label="Decision style" value={di.decision_style} />
              <StatPill label="Trust anchor" value={di.trust_anchor} />
              <StatPill label="Value driver" value={di.primary_value_orientation} />
              <StatPill label="Risk appetite" value={di.risk_appetite} />
              <StatPill label="Price sensitivity" value={bt.price_sensitivity.band} />
              <div className="border border-parchment/10 px-4 py-3">
                <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-1">Consistency</p>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 h-px bg-parchment/10">
                    <div className="h-px bg-signal" style={{ width: `${di.consistency_score}%` }} />
                  </div>
                  <span className="font-mono text-[10px] text-static">{di.consistency_score}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Narrative — first person */}
      <Section label="In their own words">
        <blockquote className="border-l-2 border-signal pl-5 text-parchment/80 text-sm leading-relaxed italic">
          &ldquo;{persona.narrative.first_person}&rdquo;
        </blockquote>
      </Section>

      {/* Identity & values */}
      <Section label="Identity">
        <p className="text-parchment/80 text-sm leading-relaxed mb-6">
          {persona.memory.core.identity_statement}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div>
            <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-3">Core values</p>
            <ul className="space-y-1.5">
              {persona.memory.core.key_values.map((v, i) => (
                <li key={i} className="flex gap-2 text-sm text-parchment/75">
                  <span className="text-signal shrink-0">·</span>{v}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-3">Key tensions</p>
            <ul className="space-y-1.5">
              {di.key_tensions.map((t, i) => (
                <li key={i} className="flex gap-2 text-sm text-parchment/75">
                  <span className="text-static shrink-0">·</span>{t}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      {/* Decision bullets */}
      {persona.decision_bullets.length > 0 && (
        <Section label="How they decide">
          <ul className="space-y-2">
            {persona.decision_bullets.map((b, i) => (
              <li key={i} className="flex gap-3 text-sm text-parchment/75 leading-relaxed">
                <span className="font-mono text-static shrink-0">0{i + 1}</span>
                {b}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Behaviour */}
      <Section label="Behavioural profile">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
          {/* Trust orientation */}
          <div>
            <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-4">Trust orientation</p>
            <div className="space-y-3">
              {Object.entries(bt.trust_orientation).map(([k, v]) => (
                <TrustBar key={k} label={k} value={v as number} />
              ))}
            </div>
          </div>

          {/* Objections */}
          <div>
            <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-4">Objection profile</p>
            <div className="space-y-3">
              {bt.objection_profile.map((o, i) => (
                <div key={i} className="border-l border-parchment/10 pl-3">
                  <p className="text-xs font-medium text-parchment/80 capitalize">{o.type.replace(/_/g, " ")}</p>
                  <p className="text-[11px] text-static mt-0.5">
                    Likelihood: {o.likelihood} · Severity: {o.severity}
                  </p>
                  {o.description && (
                    <p className="text-[11px] text-parchment/50 mt-1">{o.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Price sensitivity */}
        <div className="mt-6 border border-parchment/10 p-4">
          <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-2">
            Price sensitivity · <span className="text-parchment capitalize">{bt.price_sensitivity.band}</span>
          </p>
          <p className="text-sm text-parchment/70">{bt.price_sensitivity.description}</p>
        </div>
      </Section>

      {/* Life stories */}
      {persona.life_stories.length > 0 && (
        <Section label="Life stories">
          <div className="space-y-6">
            {persona.life_stories.map((s, i) => (
              <div key={i} className="border-l-2 border-parchment/10 pl-5">
                <div className="flex items-baseline justify-between mb-2">
                  <h3 className="font-condensed font-bold text-parchment text-lg">{s.title}</h3>
                  <span className="font-mono text-[10px] text-static capitalize ml-4 shrink-0">
                    {s.emotional_weight}
                    {s.age_at_event ? ` · age ${s.age_at_event}` : ""}
                  </span>
                </div>
                <p className="text-sm text-parchment/70 leading-relaxed">{s.narrative}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Life-defining events */}
      {persona.memory.core.life_defining_events.length > 0 && (
        <Section label="Defining moments">
          <ul className="space-y-2">
            {persona.memory.core.life_defining_events.map((e, i) => (
              <li key={i} className="flex gap-3 text-sm text-parchment/70 leading-relaxed">
                <span className="text-signal shrink-0 mt-0.5">·</span>{e}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Attributes */}
      {Object.keys(persona.attributes).length > 0 && (
        <Section label="All attributes">
          <p className="text-xs text-static mb-4">
            {Object.values(persona.attributes).reduce((n, cat) => n + Object.keys(cat).length, 0)} total attributes
            across {Object.keys(persona.attributes).length} categories
          </p>
          <div className="border border-parchment/10 px-4">
            {Object.entries(persona.attributes).map(([cat, attrs]) => (
              <AttributeCategory key={cat} category={cat} attrs={attrs} />
            ))}
          </div>
        </Section>
      )}

      {/* Demographics detail */}
      <Section label="Demographics">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <StatPill label="Occupation" value={da.employment.occupation} />
          <StatPill label="Industry" value={da.employment.industry} />
          <StatPill label="Seniority" value={da.employment.seniority} />
          <StatPill label="Education" value={da.education} />
          <StatPill label="Household size" value={String(da.household.size)} />
          <StatPill label="Composition" value={da.household.composition} />
        </div>
        {da.household.monthly_income_inr && (
          <p className="text-xs text-static mt-3 font-mono">
            Monthly income: ₹{da.household.monthly_income_inr.toLocaleString("en-IN")}
          </p>
        )}
      </Section>

      {/* Footer */}
      <div className="mt-16 pt-6 border-t border-parchment/10 flex items-center justify-between">
        <Link
          href="/"
          className="font-mono text-[10px] text-static hover:text-parchment/50 transition-colors"
        >
          ← Home
        </Link>
        <a
          href="mailto:mind@simulatte.io?subject=The%20Mind%20%E2%80%94%20feedback"
          className="font-mono text-[10px] text-static hover:text-signal transition-colors"
        >
          mind@simulatte.io
        </a>
      </div>
    </main>
  );
}
