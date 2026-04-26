"use client";

import { useState } from "react";
import { QualityAssessment } from "@/lib/api";

function ComponentBar({ label, value, description }: { label: string; value: number; description: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 mb-1">
        <span className="text-xs text-parchment/80 capitalize">{label}</span>
        <span className="font-mono text-[10px] text-static">{value.toFixed(2)}</span>
      </div>
      <div className="h-px bg-parchment/10">
        <div className="h-px bg-signal transition-all" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-[11px] text-static mt-1.5 leading-relaxed">{description}</p>
    </div>
  );
}

export default function GenuinenessChip({ assessment }: { assessment: QualityAssessment }) {
  const [open, setOpen] = useState(false);

  const score = assessment.score;
  const tone =
    score >= 7 ? "text-signal" : score >= 4 ? "text-parchment" : "text-static";
  const interpretation =
    score >= 7
      ? "Strong genuineness — anchored demographics, coherent psychology, layered narrative."
      : score >= 4
      ? "Moderate genuineness — populated profile but with thin patches in narrative or psychology."
      : "Weak genuineness — sparse or inconsistent fields; treat outputs as directional only.";

  return (
    <div className="inline-block">
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

          <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-3">
            Components
          </p>
          <div className="space-y-4 mb-6">
            {assessment.components.map((c) => (
              <ComponentBar key={c.key} label={c.label} value={c.value} description={c.description} />
            ))}
          </div>

          <p className="text-[10px] font-mono text-static uppercase tracking-widest mb-3">
            Ground-truth sources
          </p>
          <ul className="space-y-3">
            {assessment.sources.map((s) => (
              <li key={s.name} className="border-l border-parchment/10 pl-3">
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="text-xs text-parchment/85 font-medium">{s.name}</span>
                  <span className="font-mono text-[9px] text-static uppercase tracking-widest border border-parchment/15 px-1.5 py-px">
                    {s.weight}
                  </span>
                </div>
                <p className="text-[11px] text-static leading-relaxed">{s.description}</p>
              </li>
            ))}
          </ul>

          <p className="mt-5 text-[10px] font-mono text-static uppercase tracking-widest">
            What this means
          </p>
          <p className="text-[11px] text-parchment/70 mt-1.5 leading-relaxed">
            The score weights demographic grounding (40%), behavioural consistency (30%), narrative
            depth (15%), and psychological completeness (15%). Higher scores mean a persona that is
            more believable, internally consistent, and safer to act on.
          </p>
        </div>
      )}
    </div>
  );
}
