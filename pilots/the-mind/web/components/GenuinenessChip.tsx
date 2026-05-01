"use client";

import { useState } from "react";
import { QualityAssessment } from "@/lib/api";

function ComponentBar({
  label,
  value,
  description,
  weakest,
}: {
  label: string;
  value: number;
  description: string;
  weakest: boolean;
}) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 mb-1">
        <span className={`text-xs capitalize ${weakest ? "text-parchment/90" : "text-parchment/70"}`}>
          {label}
          {weakest && (
            <span className="ml-2 text-[9px] font-mono text-static uppercase tracking-widest border border-parchment/15 px-1.5 py-px">
              probe harder
            </span>
          )}
        </span>
        <span className={`font-mono text-[10px] ${weakest ? "text-parchment/60" : "text-static"}`}>
          {value.toFixed(2)}
        </span>
      </div>
      <div className="h-px bg-parchment/10">
        <div
          className={`h-px transition-all ${weakest ? "bg-parchment/40" : "bg-signal"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-[11px] text-static mt-1.5 leading-relaxed">{description}</p>
    </div>
  );
}

function SourceTag({ weight }: { weight: string }) {
  // Normalise the source weight label
  const display =
    weight === "primary" ? "Primary"
    : weight === "inferred" ? "Inferred"
    : weight === "synthesised" || weight === "synthesized" ? "Synthesised"
    : weight;
  return (
    <span className="font-mono text-[9px] text-static uppercase tracking-widest border border-parchment/15 px-1.5 py-px">
      {display}
    </span>
  );
}

export default function GenuinenessChip({ assessment }: { assessment: QualityAssessment }) {
  // Open by default so sources are immediately visible
  const [open, setOpen] = useState(true);

  const score = assessment.score;
  const tone =
    score >= 7 ? "text-signal" : score >= 4 ? "text-parchment" : "text-static";
  const interpretation =
    score >= 7
      ? "Strong genuineness — anchored demographics, coherent psychology, layered narrative."
      : score >= 4
      ? "Moderate genuineness — populated profile but with thin patches in narrative or psychology."
      : "Weak genuineness — sparse or inconsistent fields; treat outputs as directional only.";

  // Find the weakest component to surface a "probe harder" signal
  const weakestComponent = assessment.components.reduce((min, c) =>
    c.value < min.value ? c : min
  , assessment.components[0]);

  return (
    <div className="w-full">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-2 border border-parchment/15 px-3 py-1.5 hover:border-parchment/30 transition-colors"
        aria-expanded={open}
      >
        <span className="text-[10px] font-mono text-static uppercase tracking-widest">
          Genuineness
        </span>
        <span className={`font-condensed font-bold text-base leading-none ${tone}`}>
          {score.toFixed(1)}
        </span>
        <span className="font-mono text-[10px] text-static">/10</span>
        <span
          className={`text-static text-[10px] inline-block transition-transform ${open ? "rotate-90" : ""}`}
        >
          ▶
        </span>
      </button>

      {open && (
        <div className="mt-3 border border-parchment/10 p-5 max-w-xl bg-parchment/[0.02]">
          <p className="text-[11px] text-parchment/70 leading-relaxed mb-5">{interpretation}</p>

          {/* Sources — shown first, before components */}
          <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-3">
            Data sources
          </p>
          <ul className="space-y-3 mb-6">
            {assessment.sources.map((s) => {
              // Reframe the LLM source name to methodology-focused wording
              const displayName =
                s.name === "LLM Inference (Anthropic Claude)" ||
                s.name === "LLM Inference"
                  ? "Structured inference"
                  : s.name;
              const displayDesc =
                s.name === "LLM Inference (Anthropic Claude)" ||
                s.name === "LLM Inference"
                  ? "Cross-referenced signals from public sources, synthesised into behavioural patterns using validated psychographic models."
                  : s.description;
              return (
                <li key={s.name} className="border-l border-parchment/10 pl-3">
                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="text-xs text-parchment/85 font-medium">{displayName}</span>
                    <SourceTag weight={s.weight} />
                  </div>
                  <p className="text-[11px] text-static leading-relaxed">{displayDesc}</p>
                </li>
              );
            })}
          </ul>

          {/* Score components */}
          <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-3">
            Score components
          </p>
          <div className="space-y-4 mb-6">
            {assessment.components.map((c) => (
              <ComponentBar
                key={c.key}
                label={c.label}
                value={c.value}
                description={c.description}
                weakest={c.key === weakestComponent?.key}
              />
            ))}
          </div>

          <p className="mt-5 text-[10px] font-mono text-static uppercase tracking-widest">
            How this is scored
          </p>
          <p className="text-[11px] text-parchment/70 mt-1.5 leading-relaxed">
            Weights demographic grounding (40%), behavioural consistency (30%), narrative
            depth (15%), and psychological completeness (15%). Higher scores indicate a
            persona that is more believable, internally consistent, and safer to act on.
          </p>
        </div>
      )}
    </div>
  );
}
