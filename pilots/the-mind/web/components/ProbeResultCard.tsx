"use client";

import { useState } from "react";
import Link from "next/link";
import { ProbeResult, API } from "@/lib/api";

// ── helpers ────────────────────────────────────────────────────────────────

function ScoreBar({ score, max = 10 }: { score: number; max?: number }) {
  const pct = Math.round((score / max) * 100);
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-px bg-parchment/10">
        <div className="h-px bg-signal transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-parchment w-8 text-right">{score}/{max}</span>
    </div>
  );
}

function SectionHeader({ label }: { label: string }) {
  return (
    <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-6">
      {label}
    </p>
  );
}

function QuestionBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-parchment/10 pt-6 mt-6">
      <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-3">{title}</p>
      {children}
    </div>
  );
}

// ── share modal ───────────────────────────────────────────────────────────

function ShareModal({ probe, onClose }: { probe: ProbeResult; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  const publicUrl = `https://mind.simulatte.io/probe/${probe.probe_id}`;
  const tweetText = encodeURIComponent(
    `I asked an AI persona of ${probe.persona_name} what they'd think of ${probe.product_name}. Verdict: ${probe.purchase_intent.score}/10.\n\nTry it on @SimulatteAI: ${publicUrl}`
  );
  const liText = encodeURIComponent(
    `Just ran a Simulatte simulation: tested ${probe.product_name} with ${probe.persona_name}. Purchase intent: ${probe.purchase_intent.score}/10. Top objection: "${probe.top_objection}"\n\nTry it: ${publicUrl}`
  );

  function copyLink() {
    navigator.clipboard.writeText(publicUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-void/80 px-4">
      <div className="w-full max-w-md border border-parchment/20 bg-void p-6">
        <div className="flex items-center justify-between mb-6">
          <p className="text-[11px] font-mono text-static uppercase tracking-widest">Share this verdict</p>
          <button onClick={onClose} className="text-static hover:text-parchment/50 font-mono text-lg leading-none">&times;</button>
        </div>

        {/* Mini verdict preview */}
        <div className="border border-parchment/10 p-4 mb-6">
          <p className="text-[10px] font-mono text-static mb-1">{probe.persona_name} on {probe.product_name}</p>
          <p className="font-condensed font-bold text-parchment text-xl">Purchase intent {probe.purchase_intent.score}/10</p>
          <p className="text-xs text-parchment/60 mt-1 line-clamp-2">&ldquo;{probe.purchase_intent.rationale}&rdquo;</p>
        </div>

        <div className="flex gap-3 mb-4">
          <a
            href={`https://twitter.com/intent/tweet?text=${tweetText}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 border border-parchment/20 px-4 py-2.5 text-center font-condensed font-bold text-parchment text-sm hover:bg-parchment/5 transition-colors"
          >
            Tweet
          </a>
          <a
            href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(publicUrl)}&summary=${liText}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 border border-parchment/20 px-4 py-2.5 text-center font-condensed font-bold text-parchment text-sm hover:bg-parchment/5 transition-colors"
          >
            LinkedIn
          </a>
          <button
            onClick={copyLink}
            className="flex-1 border border-parchment/20 px-4 py-2.5 font-condensed font-bold text-parchment text-sm hover:bg-parchment/5 transition-colors"
          >
            {copied ? "Copied!" : "Copy link"}
          </button>
        </div>

        <div className="border border-parchment/10 px-3 py-2.5">
          <p className="text-[10px] font-mono text-static mb-1">Public link</p>
          <p className="font-mono text-[11px] text-parchment/70 break-all">{publicUrl}</p>
        </div>
      </div>
    </div>
  );
}

// ── main card ─────────────────────────────────────────────────────────────

interface ProbeResultCardProps {
  probe: ProbeResult;
  personaId?: string;       // present on auth pages, absent on public share
  isPublic?: boolean;
}

export default function ProbeResultCard({ probe, personaId, isPublic = false }: ProbeResultCardProps) {
  const [shareOpen, setShareOpen] = useState(false);

  return (
    <div className="max-w-3xl mx-auto">
      {/* Persona + product header */}
      <div className="flex items-start gap-4 mb-8">
        {probe.persona_portrait_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={probe.persona_portrait_url}
            alt={probe.persona_name}
            className="w-16 h-16 object-cover border border-parchment/10 shrink-0"
          />
        )}
        <div>
          <p className="text-[11px] font-sans font-semibold tracking-widest uppercase text-signal mb-1">
            Litmus Probe
          </p>
          <h1 className="font-condensed font-bold text-parchment leading-none mb-1"
            style={{ fontSize: "clamp(24px,3.5vw,40px)" }}>
            {probe.product_name}
          </h1>
          <p className="text-static text-sm">
            {probe.persona_name} &middot; {probe.category}
          </p>
        </div>
      </div>

      {/* ── REACTION ─────────────────────────────────────────────────────── */}
      <section>
        <SectionHeader label="Reaction" />

        <QuestionBlock title="Purchase intent">
          <div className="mb-3">
            <ScoreBar score={probe.purchase_intent.score} />
          </div>
          <p className="text-sm text-parchment/80 leading-relaxed">
            &ldquo;{probe.purchase_intent.rationale}&rdquo;
          </p>
        </QuestionBlock>

        <QuestionBlock title="First impression">
          <div className="flex flex-wrap gap-2 mb-3">
            {probe.first_impression.adjectives.map((adj, i) => (
              <span key={i} className="border border-parchment/20 px-3 py-1 font-mono text-[11px] text-parchment/80 uppercase tracking-wide">
                {adj}
              </span>
            ))}
          </div>
          <p className="text-sm text-parchment/70 italic">{probe.first_impression.feeling}</p>
        </QuestionBlock>
      </section>

      {/* ── BELIEF ───────────────────────────────────────────────────────── */}
      <section className="border-t border-parchment/10 pt-8 mt-8">
        <SectionHeader label="Belief" />

        {probe.claim_believability.length > 0 && (
          <QuestionBlock title="Claim believability">
            <div className="space-y-4">
              {probe.claim_believability.map((cv, i) => (
                <div key={i} className="border-l border-parchment/10 pl-4">
                  <p className="text-[11px] text-parchment/60 mb-1.5 italic">&ldquo;{cv.claim}&rdquo;</p>
                  <ScoreBar score={cv.score} />
                  <p className="text-[11px] text-parchment/70 mt-1.5">{cv.comment}</p>
                </div>
              ))}
            </div>
          </QuestionBlock>
        )}

        <QuestionBlock title="Differentiation">
          <div className="mb-3">
            <ScoreBar score={probe.differentiation.score} />
          </div>
          <p className="text-sm text-parchment/80 leading-relaxed">{probe.differentiation.comment}</p>
        </QuestionBlock>
      </section>

      {/* ── FRICTION ─────────────────────────────────────────────────────── */}
      <section className="border-t border-parchment/10 pt-8 mt-8">
        <SectionHeader label="Friction" />

        <QuestionBlock title="Top objection">
          <div className="border-l-2 border-signal pl-4">
            <p className="text-sm text-parchment/80 leading-relaxed">{probe.top_objection}</p>
          </div>
        </QuestionBlock>

        <QuestionBlock title="Trust signals needed">
          <ul className="space-y-2">
            {probe.trust_signals_needed.map((s, i) => (
              <li key={i} className="flex gap-2 text-sm text-parchment/75 leading-relaxed">
                <span className="text-signal shrink-0 mt-0.5">·</span>{s}
              </li>
            ))}
          </ul>
        </QuestionBlock>
      </section>

      {/* ── COMMITMENT ───────────────────────────────────────────────────── */}
      <section className="border-t border-parchment/10 pt-8 mt-8">
        <SectionHeader label="Commitment" />

        <QuestionBlock title="Price willingness">
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="border border-parchment/10 px-4 py-3">
              <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-1">WTP low</p>
              <p className="text-sm text-parchment font-medium">{probe.price_willingness.wtp_low || "—"}</p>
            </div>
            <div className="border border-parchment/10 px-4 py-3">
              <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-1">WTP high</p>
              <p className="text-sm text-parchment font-medium">{probe.price_willingness.wtp_high || "—"}</p>
            </div>
          </div>
          <p className="text-sm text-parchment/80 leading-relaxed">{probe.price_willingness.reaction}</p>
        </QuestionBlock>

        <QuestionBlock title="Word of mouth">
          <div className="mb-3">
            <ScoreBar score={probe.word_of_mouth.likelihood} />
          </div>
          <p className="text-sm text-parchment/80 italic leading-relaxed">
            &ldquo;{probe.word_of_mouth.what_theyd_say}&rdquo;
          </p>
        </QuestionBlock>
      </section>

      {/* ── Actions ──────────────────────────────────────────────────────── */}
      <div className="border-t border-parchment/10 pt-8 mt-8 space-y-4">
        <div className="flex flex-wrap gap-3">
          {personaId && (
            <Link
              href={`/persona/${personaId}/chat?context=${probe.probe_id}`}
              className="inline-flex items-center gap-2 bg-signal text-void font-condensed font-bold px-4 py-2.5 hover:bg-signal/90 transition-colors"
            >
              <span className="text-[11px] tracking-widest uppercase">Continue chat about this product</span>
              <span aria-hidden>→</span>
            </Link>
          )}

          <button
            onClick={() => setShareOpen(true)}
            className="inline-flex items-center gap-2 border border-parchment/20 text-parchment font-condensed font-bold px-4 py-2.5 hover:bg-parchment/5 transition-colors"
          >
            <span className="text-[11px] tracking-widest uppercase">Share verdict</span>
            <span aria-hidden>↗</span>
          </button>

          <a
            href="https://calendly.com/iqbal-simulatte"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 border border-parchment/10 text-parchment/60 font-condensed font-bold px-4 py-2.5 hover:border-parchment/20 hover:text-parchment/80 transition-colors"
          >
            <span className="text-[11px] tracking-widest uppercase">Book a simulation call</span>
            <span aria-hidden>→</span>
          </a>
        </div>

        <div className="flex flex-wrap gap-3">
          {!isPublic && (
            <Link
              href="/generate"
              className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors"
            >
              Test with another persona →
            </Link>
          )}
          {isPublic && (
            <Link
              href="/generate"
              className="text-[11px] font-mono text-static hover:text-parchment/50 transition-colors"
            >
              Generate your own persona →
            </Link>
          )}
        </div>
      </div>

      {/* Metadata footer */}
      <div className="mt-10 pt-6 border-t border-parchment/10 flex items-center justify-between">
        <span className="font-mono text-[10px] text-static">{probe.probe_id}</span>
        <span className="font-mono text-[10px] text-static">
          {new Date(probe.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
        </span>
      </div>

      {shareOpen && <ShareModal probe={probe} onClose={() => setShareOpen(false)} />}
    </div>
  );
}
