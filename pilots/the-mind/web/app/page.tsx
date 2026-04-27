"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchPersonas, PersonaCard } from "@/lib/api";
import PersonaDrawer from "@/components/PersonaDrawer";
import WallOfVoices from "@/components/WallOfVoices";
import ProbeTicker from "@/components/ProbeTicker";
import LivePersonaWall from "@/components/LivePersonaWall";

// ─── Mind mark inline SVG ────────────────────────────────────────────────────
function MindMark({ size = 32, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path d="M 10,26.392 A 12,12 0 1 0 10,5.608" stroke="#E9E6DF" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M 12.5,22.062 A 7,7 0 1 0 12.5,9.938" stroke="#E9E6DF" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="16" cy="16" r="3" fill="#A8FF3E" />
    </svg>
  );
}

// ─── Exemplar strip — client side so drawer state works ─────────────────────
function ExemplarStrip({ personas }: { personas: PersonaCard[] }) {
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [activeCard, setActiveCard] = useState<PersonaCard | null>(null);

  function open(p: PersonaCard) {
    setActiveCard(p);
    setActiveSlug(p.slug);
  }

  return (
    <>
      <div className="flex gap-4 overflow-x-auto pb-2 snap-x snap-mandatory" style={{ scrollbarWidth: "none" }}>
        {personas.map((p) => (
          <button
            key={p.slug}
            onClick={() => open(p)}
            className="snap-start flex-shrink-0 w-48 border border-parchment/10 bg-void p-4 text-left hover:border-parchment/30 transition-colors"
          >
            {p.portrait_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={p.portrait_url}
                alt={p.name}
                className="w-full aspect-square object-cover mb-3"
                style={{ filter: "grayscale(0.15)" }}
              />
            ) : (
              <div className="w-full aspect-square bg-parchment/5 mb-3 flex items-center justify-center">
                <MindMark size={24} />
              </div>
            )}
            <div className="font-condensed font-bold text-parchment text-base leading-tight mb-1">{p.name}</div>
            <div className="font-sans text-[11px] text-static leading-snug">{p.age} · {p.city}</div>
            <div className="mt-2 font-sans text-[11px] text-parchment/72 leading-snug line-clamp-2">{p.description}</div>
          </button>
        ))}
      </div>

      <PersonaDrawer
        slug={activeSlug}
        initialCard={activeCard}
        onClose={() => { setActiveSlug(null); setActiveCard(null); }}
      />
    </>
  );
}

// ─── Litmus demo mock ────────────────────────────────────────────────────────
function LitmusDemo() {
  const questions = [
    { label: "Purchase Intent", value: "7.2 / 10", note: "Would consider buying at the right moment." },
    { label: "First Impression", value: "Curious, lean", note: "Clean aesthetic reads as premium without trying." },
    { label: "Claim Believability", value: "8.1 / 10", note: "\"High-protein, natural\" claims land well." },
    { label: "Top Objection", value: "Price anchor", note: "₹120/bar feels steep vs. a full meal." },
  ];

  const [revealed, setRevealed] = useState(0);

  useEffect(() => {
    if (revealed >= questions.length) return;
    const t = setTimeout(() => setRevealed((r) => r + 1), 900);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revealed]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-0 border border-parchment/10">
      {/* Brief side */}
      <div className="border-b md:border-b-0 md:border-r border-parchment/10 p-6 md:p-8">
        <div className="font-sans text-[11px] font-semibold tracking-widest uppercase text-signal mb-4">Product brief</div>
        <div className="font-condensed font-bold text-parchment text-xl mb-3">HelloDay Energy Bar</div>
        <div className="font-sans text-[13px] text-parchment/80 leading-relaxed mb-4">
          A 200-calorie natural energy bar targeting urban professionals aged 25–35.
          High-protein (12g), no refined sugar. Positioned as the mid-morning alternative
          to a second coffee.
        </div>
        <div className="space-y-2">
          {["High-protein, naturally sweetened", "Clean-label, 6 ingredients", "₹120 per bar"].map((claim) => (
            <div key={claim} className="flex items-center gap-2">
              <div className="w-1 h-1 bg-signal flex-shrink-0" />
              <span className="font-sans text-[12px] text-parchment/72">{claim}</span>
            </div>
          ))}
        </div>
        <div className="mt-6 pt-4 border-t border-parchment/10">
          <div className="font-mono text-[10px] text-static tracking-widest uppercase">Tested on: Arun, 29, Bangalore</div>
        </div>
      </div>

      {/* Results side */}
      <div className="p-6 md:p-8">
        <div className="flex items-center justify-between mb-4">
          <div className="font-sans text-[11px] font-semibold tracking-widest uppercase text-signal">Probe results</div>
          <div className="font-mono text-[9px] text-static tracking-widest uppercase border border-parchment/10 px-2 py-1">preview</div>
        </div>
        <div className="space-y-3">
          {questions.map((q, i) => (
            <div
              key={q.label}
              className="border border-parchment/10 p-3 transition-all"
              style={{
                opacity: i < revealed ? 1 : 0,
                transform: i < revealed ? "translateY(0)" : "translateY(6px)",
                transition: "opacity 0.4s ease, transform 0.4s ease",
              }}
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <span className="font-sans text-[11px] font-semibold text-static tracking-wide uppercase">{q.label}</span>
                <span className="font-condensed font-bold text-signal text-sm flex-shrink-0">{q.value}</span>
              </div>
              <p className="font-sans text-[12px] text-parchment/72 leading-snug">{q.note}</p>
            </div>
          ))}
        </div>
        {revealed >= questions.length && (
          <div className="mt-4 pt-4 border-t border-parchment/10 flex items-center gap-2">
            <div className="w-2 h-2 bg-signal" style={{ animation: "dotPulse 2.2s ease-in-out infinite" }} />
            <span className="font-mono text-[10px] text-signal tracking-widest uppercase">8 questions · ~20s</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── How it works step ───────────────────────────────────────────────────────
function Step({ n, title, body, diagram }: { n: string; title: string; body: string; diagram: React.ReactNode }) {
  return (
    <div className="border border-parchment/10 p-6 md:p-8">
      <div className="font-mono text-[11px] text-static tracking-widest uppercase mb-4">{n}</div>
      <div className="mb-4">{diagram}</div>
      <h3 className="font-condensed font-bold text-parchment text-xl leading-tight mb-2">{title}</h3>
      <p className="font-sans text-[14px] text-parchment/80 leading-relaxed">{body}</p>
    </div>
  );
}

// ─── Genuineness component row ───────────────────────────────────────────────
function GenuinenessRow({ label, value, note }: { label: string; value: number; note: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className="border border-parchment/10 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="font-sans text-[13px] font-semibold text-parchment">{label}</span>
        <span className="font-condensed font-bold text-signal text-base">{pct}%</span>
      </div>
      <div className="h-px bg-parchment/10 mb-3">
        <div className="h-px bg-signal" style={{ width: `${pct}%` }} />
      </div>
      <p className="font-sans text-[12px] text-parchment/72 leading-snug">{note}</p>
    </div>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────
export default function HomePage() {
  const [personas, setPersonas] = useState<PersonaCard[]>([]);

  useEffect(() => {
    fetchPersonas()
      .then(setPersonas)
      .catch(() => {/* silent on error */});
  }, []);

  return (
    <>
      {/* ── Keyframe animations ── */}
      <style>{`
        @keyframes dotPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.3; transform: scale(0.85); }
        }
      `}</style>

      <main className="bg-void text-parchment">

        {/* ══════════════════════════════════════════════════════
            SECTION 1 — HERO  (live persona wall + headline)
        ══════════════════════════════════════════════════════ */}
        <section
          className="relative min-h-screen flex flex-col justify-between overflow-hidden"
          style={{ maxWidth: "none" }}
        >
          {/* Drifting persona wall, real portraits from /community/personas */}
          <LivePersonaWall />

          {/* Top lockup — small, anchored top-left */}
          <div className="relative z-10 px-6 md:px-14 pt-8">
            <div className="flex items-center gap-3">
              <MindMark size={28} />
              <span className="font-condensed font-bold text-parchment text-base tracking-wide">Mind</span>
              <span className="font-sans text-[11px] text-static tracking-widest uppercase">by Simulatte</span>
            </div>
          </div>

          {/* Foreground content — centred bottom-left so the wall reads
              edge-to-edge above and the reader's eye lands on the heading
              against the darkest part of the gradient. */}
          <div className="relative z-10 px-6 md:px-14 pb-20 pt-12 text-center">
            {/* Eyebrow */}
            <div className="flex items-center justify-center gap-3 mb-5">
              <span className="w-6 h-px bg-parchment/20" />
              <span className="font-sans font-semibold text-[11px] tracking-widest uppercase text-static">
                Decision infrastructure
              </span>
              <span className="w-6 h-px bg-parchment/20" />
            </div>

            {/* Hero heading — split lettering, single green word */}
            <h1
              className="font-condensed font-extrabold text-parchment mb-6 mx-auto"
              style={{
                fontSize: "clamp(48px, 6.5vw, 92px)",
                lineHeight: 0.96,
                letterSpacing: "-0.008em",
                textShadow: "0 2px 24px rgba(5,5,5,0.85)",
                maxWidth: "18ch",
              }}
            >
              Before you ship it, <span className="text-signal">talk</span> to the person you built it for.
            </h1>

            {/* Subtitle */}
            <p
              className="font-sans text-parchment/88 leading-relaxed mx-auto mb-10"
              style={{
                fontSize: "16px",
                lineHeight: 1.78,
                maxWidth: "640px",
                textShadow: "0 1px 16px rgba(5,5,5,0.85)",
              }}
            >
              The Mind generates a behaviourally coherent human from a paragraph —
              anchored in real population data, not a generic average. Every face
              drifting above is a real person someone built this week. Click any of them.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap justify-center gap-3">
              <Link
                href="/generate"
                className="font-mono text-[11px] font-medium tracking-widest uppercase px-7 py-3 bg-signal text-void hover:opacity-90 transition-opacity"
              >
                Build a person →
              </Link>
              <Link
                href="/community"
                className="font-mono text-[11px] font-medium tracking-widest uppercase px-7 py-3 border border-parchment/30 text-parchment hover:border-parchment hover:bg-parchment/5 transition-colors backdrop-blur-sm"
              >
                Browse the wall
              </Link>
            </div>
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════
            PROBE TICKER — recent pulses (curated, privacy-preserving)
        ══════════════════════════════════════════════════════ */}
        <ProbeTicker />

        {/* ══════════════════════════════════════════════════════
            SECTION 2 — LIVE EXEMPLARS
        ══════════════════════════════════════════════════════ */}
        <section id="exemplars" className="px-6 md:px-14 py-20 max-w-screen-xl mx-auto">
          {/* Divider */}
          <div className="h-px bg-parchment/8 mb-16" />

          <div className="flex items-center gap-3 mb-4">
            <span className="font-sans font-semibold text-[11px] tracking-widest uppercase text-signal">Live personas</span>
            <span className="w-6 h-px bg-signal/30" />
          </div>
          <h2
            className="font-condensed font-extrabold text-parchment mb-3"
            style={{ fontSize: "clamp(36px, 5vw, 56px)", lineHeight: 1.0, letterSpacing: "-0.01em" }}
          >
            Five people we&apos;ve already built.
          </h2>
          <p className="font-sans text-base text-parchment/80 mb-10 max-w-xl" style={{ lineHeight: 1.78 }}>
            Each has 200+ attributes, a decision psychology, life stories, and an opinion on your product.
            Click any card to talk to them.
          </p>

          {personas.length > 0 ? (
            <ExemplarStrip personas={personas} />
          ) : (
            <div className="border border-parchment/10 p-6">
              <p className="font-mono text-[11px] text-static tracking-widest uppercase">Loading personas…</p>
            </div>
          )}
        </section>

        {/* ══════════════════════════════════════════════════════
            WALL OF VOICES — drifting persona-quote columns
        ══════════════════════════════════════════════════════ */}
        <WallOfVoices />

        {/* ══════════════════════════════════════════════════════
            SECTION 3 — LITMUS PROBE DEMO
        ══════════════════════════════════════════════════════ */}
        <section className="px-6 md:px-14 py-20 max-w-screen-xl mx-auto">
          <div className="h-px bg-parchment/8 mb-16" />

          <div className="flex items-center gap-3 mb-4">
            <span className="font-sans font-semibold text-[11px] tracking-widest uppercase text-signal">Litmus probe</span>
            <span className="w-6 h-px bg-signal/30" />
          </div>
          <h2
            className="font-condensed font-extrabold text-parchment mb-3"
            style={{ fontSize: "clamp(36px, 5vw, 56px)", lineHeight: 1.0, letterSpacing: "-0.01em" }}
          >
            Test any product against any{" "}
            <span className="text-signal">person,</span>
            <br />in 30 seconds.
          </h2>
          <p className="font-sans text-base text-parchment/80 mb-10 max-w-xl" style={{ lineHeight: 1.78 }}>
            Drop in a product brief. The probe runs 8 structured questions in parallel —
            purchase intent, objections, price willingness, word-of-mouth likelihood.
          </p>

          <LitmusDemo />

          <div className="mt-8">
            <Link
              href="/generate"
              className="font-mono text-[11px] font-medium tracking-widest uppercase px-7 py-3 border border-signal text-signal hover:bg-signal/10 transition-colors"
            >
              Run your own probe →
            </Link>
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════
            SECTION 4 — HOW IT WORKS
        ══════════════════════════════════════════════════════ */}
        <section className="px-6 md:px-14 py-20 max-w-screen-xl mx-auto">
          <div className="h-px bg-parchment/8 mb-16" />

          <div className="flex items-center gap-3 mb-4">
            <span className="font-sans font-semibold text-[11px] tracking-widest uppercase text-signal">How it works</span>
            <span className="w-6 h-px bg-signal/30" />
          </div>
          <h2
            className="font-condensed font-extrabold text-parchment mb-10"
            style={{ fontSize: "clamp(36px, 5vw, 56px)", lineHeight: 1.0, letterSpacing: "-0.01em" }}
          >
            Three steps from brief to verdict.
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Step
              n="01"
              title="Describe the person"
              body="Write a paragraph. Age, city, job, what keeps them up at night. That&apos;s enough to anchor a full psychology."
              diagram={
                <div className="border border-parchment/10 p-3 bg-parchment/[0.02]">
                  <div className="font-mono text-[10px] text-static mb-2 tracking-widest uppercase">persona brief</div>
                  <div className="space-y-1">
                    {["Arun, 29, Bangalore", "Software engineer at a Series B startup", "Spends ₹3–4k/mo on fitness"].map((l) => (
                      <div key={l} className="h-2 bg-parchment/10" style={{ width: l.length * 5 + "px", maxWidth: "100%" }} />
                    ))}
                  </div>
                </div>
              }
            />
            <Step
              n="02"
              title="We anchor them in real data"
              body="The engine grounds every attribute in census-derived population statistics. No hallucination — every value has a source."
              diagram={
                <div className="border border-parchment/10 p-3 bg-parchment/[0.02]">
                  <div className="font-mono text-[10px] text-static mb-3 tracking-widest uppercase">demographic anchor</div>
                  <div className="space-y-2">
                    {[
                      { label: "Income band", pct: 68 },
                      { label: "Trust index", pct: 82 },
                      { label: "Risk appetite", pct: 44 },
                    ].map((row) => (
                      <div key={row.label} className="flex items-center gap-2">
                        <span className="font-sans text-[10px] text-static w-20 flex-shrink-0">{row.label}</span>
                        <div className="flex-1 h-px bg-parchment/10">
                          <div className="h-px bg-signal" style={{ width: `${row.pct}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              }
            />
            <Step
              n="03"
              title="Probe their decisions"
              body="Run a Litmus probe or start a chat. Every response is consistent with who this person is — not a generic average."
              diagram={
                <div className="border border-parchment/10 p-3 bg-parchment/[0.02]">
                  <div className="font-mono text-[10px] text-static mb-3 tracking-widest uppercase">litmus verdict</div>
                  <div className="space-y-2">
                    {[
                      { label: "Purchase intent", value: "7.2" },
                      { label: "WTP", value: "₹95" },
                    ].map((row) => (
                      <div key={row.label} className="flex items-center justify-between">
                        <span className="font-sans text-[10px] text-static">{row.label}</span>
                        <span className="font-condensed font-bold text-signal text-sm">{row.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              }
            />
          </div>

          <div className="mt-10 border border-parchment/10 p-5">
            <p className="font-sans text-[13px] text-parchment/72 leading-relaxed">
              Built on the same engine that powers Simulatte&apos;s 5,000-agent population simulations.
              Every persona shares the same grounding methodology — just focused on a single individual.
            </p>
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════
            SECTION 5 — GENUINENESS TRUST STRIP
        ══════════════════════════════════════════════════════ */}
        <section className="px-6 md:px-14 py-20 max-w-screen-xl mx-auto">
          <div className="h-px bg-parchment/8 mb-16" />

          <div className="flex items-center gap-3 mb-4">
            <span className="font-sans font-semibold text-[11px] tracking-widest uppercase text-signal">Genuineness</span>
            <span className="w-6 h-px bg-signal/30" />
          </div>
          <h2
            className="font-condensed font-extrabold text-parchment mb-3"
            style={{ fontSize: "clamp(36px, 5vw, 56px)", lineHeight: 1.0, letterSpacing: "-0.01em" }}
          >
            Every persona is graded.
          </h2>
          <p className="font-sans text-base text-parchment/80 mb-10 max-w-xl" style={{ lineHeight: 1.78 }}>
            We compute a Genuineness score across four components on every generation.
            We tell you when our confidence is low — so you know how much to trust the output.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <GenuinenessRow
              label="Demographic grounding"
              value={0.87}
              note="Age, location, income, and life-stage anchored to verified population data."
            />
            <GenuinenessRow
              label="Behavioural consistency"
              value={0.81}
              note="Decision style, trust orientation, and objections are internally coherent."
            />
            <GenuinenessRow
              label="Narrative depth"
              value={0.74}
              note="Life stories and memories feel specific to this person, not generic archetypes."
            />
            <GenuinenessRow
              label="Psychological completeness"
              value={0.79}
              note="Core identity, key tensions, and coping mechanisms are all present and consistent."
            />
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════
            SECTION 6 — SOCIAL PROOF (hidden until populated)
        ══════════════════════════════════════════════════════ */}
        {/* Intentionally empty — will surface when shares table has entries */}

        {/* ══════════════════════════════════════════════════════
            SECTION 7 — CLOSING CTA
        ══════════════════════════════════════════════════════ */}
        <section
          className="relative px-6 md:px-14 py-28 overflow-hidden"
          style={{ background: "#050505", maxWidth: "none" }}
        >
          {/* Grid fade */}
          <div
            aria-hidden="true"
            className="absolute inset-0 pointer-events-none"
            style={{
              backgroundImage:
                "linear-gradient(rgba(233,230,223,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(233,230,223,0.018) 1px, transparent 1px)",
              backgroundSize: "72px 72px",
            }}
          />

          <div className="relative z-10 max-w-3xl mx-auto text-center">
            <h2
              className="font-condensed font-extrabold text-parchment mb-10"
              style={{ fontSize: "clamp(40px, 5.5vw, 72px)", lineHeight: 0.96, letterSpacing: "-0.008em" }}
            >
              The cheapest user research<br />
              you&apos;ll ever <span className="text-signal">run</span>.
            </h2>

            <p
              className="font-sans text-parchment/80 mb-10 max-w-xl mx-auto"
              style={{ fontSize: "16px", lineHeight: 1.78 }}
            >
              One paragraph in. A coherent human out. Probe their decisions, surface
              their objections, find out what they&apos;d say to a friend — in seconds,
              not weeks.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
              <Link
                href="/generate"
                className="font-mono text-[11px] font-medium tracking-widest uppercase px-8 py-4 bg-signal text-void hover:opacity-90 transition-opacity"
              >
                Build your first person →
              </Link>
            </div>

            <p className="font-sans text-[14px] text-parchment/72" style={{ lineHeight: 1.78 }}>
              Need to test against thousands?{" "}
              <a
                href="https://calendly.com/iqbal-simulatte"
                target="_blank"
                rel="noopener noreferrer"
                className="text-parchment underline underline-offset-4 decoration-parchment/30 hover:decoration-parchment/70 transition-all"
              >
                Book a call
              </a>{" "}
              about Simulatte&apos;s 5,000-agent population engine.
            </p>
          </div>
        </section>

        {/* ── Footer ── */}
        <footer className="border-t border-parchment/8 px-6 md:px-14 py-8">
          <div className="max-w-screen-xl mx-auto flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <MindMark size={20} />
              <span className="font-mono text-[10px] text-static tracking-widest uppercase">
                Simulatte / The Mind / Confidential
              </span>
            </div>
            <div className="flex items-center gap-6 flex-wrap">
              <Link
                href="/community"
                className="font-mono text-[10px] text-parchment/60 tracking-widest uppercase hover:text-signal transition-colors"
              >
                The Wall
              </Link>
              <a
                href="mailto:mind@simulatte.io?subject=The%20Mind%20%E2%80%94%20feedback"
                className="font-mono text-[10px] text-parchment/60 tracking-widest uppercase hover:text-signal transition-colors"
              >
                Questions? mind@simulatte.io
              </a>
              <span className="font-mono text-[10px] text-static tracking-widest uppercase">
                mind.simulatte.io
              </span>
            </div>
          </div>
        </footer>

      </main>
    </>
  );
}
